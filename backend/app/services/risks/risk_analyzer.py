from collections.abc import Iterable

from app.schemas.architecture import ArchitectureNode, ArchitectureSpec, ComponentKind
from app.schemas.load_profile import LoadProfileSpec, LoadScenario, LoadScenarioType
from app.schemas.requirement import StructuredRequirementSpec
from app.schemas.risk import RiskItem, RiskReport, RiskSeverity


class RiskAnalyzer:
    def analyze(
        self,
        *,
        requirement: StructuredRequirementSpec,
        architecture: ArchitectureSpec,
        load_profile: LoadProfileSpec,
    ) -> RiskReport:
        scenario = self._primary_scenario(load_profile, requirement)
        node_ids = {node.id for node in architecture.nodes}
        node_kinds = {node.kind for node in architecture.nodes}
        risks: list[RiskItem] = []

        database_risk = self._database_bottleneck_risk(requirement, architecture, scenario, node_ids)
        if database_risk is not None:
            risks.append(database_risk)

        cache_risk = self._cache_pressure_risk(requirement, architecture, scenario, node_kinds)
        if cache_risk is not None:
            risks.append(cache_risk)

        queue_risk = self._queue_lag_risk(architecture, scenario, node_kinds)
        if queue_risk is not None:
            risks.append(queue_risk)

        partition_risk = self._hot_partition_risk(requirement, architecture, scenario)
        if partition_risk is not None:
            risks.append(partition_risk)

        region_risk = self._single_region_risk(requirement, architecture)
        if region_risk is not None:
            risks.append(region_risk)

        autoscaling_risk = self._autoscaling_gap_risk(architecture, scenario)
        if autoscaling_risk is not None:
            risks.append(autoscaling_risk)

        cost_risk = self._cost_hotspot_risk(requirement, architecture, scenario)
        if cost_risk is not None:
            risks.append(cost_risk)

        scaling_actions = self._unique_lines(
            recommendation for risk in risks for recommendation in risk.recommendations
        )
        resilience_gaps = self._unique_lines(
            risk.explanation
            for risk in risks
            if risk.category in {"database_bottleneck", "queue_lag_risk", "single_region_risk", "autoscaling_gap"}
        )
        summary = (
            f"Identified {len(risks)} scaling and reliability risks for {requirement.product_name}. "
            f"The highest modeled peak load is {scenario.peak_rps} RPS with {scenario.concurrency_levels.peak_users} peak users."
        )
        return RiskReport(
            summary=summary,
            top_risks=sorted(risks, key=self._severity_rank),
            scaling_actions=scaling_actions,
            resilience_gaps=resilience_gaps,
            assumptions=requirement.assumptions,
        )

    def _database_bottleneck_risk(
        self,
        requirement: StructuredRequirementSpec,
        architecture: ArchitectureSpec,
        scenario: LoadScenario,
        node_ids: set[str],
    ) -> RiskItem | None:
        if "postgres" not in node_ids:
            return None

        has_replica = any(node.id == "postgres-replica" for node in architecture.nodes)
        write_heavy = self._request_percentage(scenario, {"POST", "PUT", "PATCH", "DELETE"}) >= 35
        severity = None
        if scenario.peak_rps >= 2_000 and not has_replica:
            severity = RiskSeverity.critical
        elif scenario.peak_rps >= 1_000 or (write_heavy and scenario.concurrency_levels.peak_users >= 4_000):
            severity = RiskSeverity.high
        elif scenario.peak_rps >= 500:
            severity = RiskSeverity.medium

        if severity is None:
            return None

        explanation = (
            "Primary transactional traffic is concentrated on PostgreSQL, and the modeled peak concurrency is high enough "
            "to cause connection pool saturation, lock contention, and hot-index pressure."
        )
        recommendation = "Add read replicas, aggressive connection pooling, and profile the hottest queries before peak traffic windows."
        return self._risk(
            title="Database bottleneck risk",
            severity=severity,
            category="database_bottleneck",
            explanation=explanation,
            recommendation=recommendation,
            affected_components=[node.id for node in architecture.databases] or ["postgres"],
            recommendations=[
                recommendation,
                "Separate analytical or search-heavy reads from the write path.",
                "Cache idempotent reads and precompute expensive query results.",
            ],
        )

    def _cache_pressure_risk(
        self,
        requirement: StructuredRequirementSpec,
        architecture: ArchitectureSpec,
        scenario: LoadScenario,
        node_kinds: set[ComponentKind],
    ) -> RiskItem | None:
        read_pressure = self._request_percentage(scenario, {"GET"}) >= 55
        cache_nodes = architecture.cache
        if not read_pressure and not cache_nodes:
            return None

        if not cache_nodes and scenario.peak_rps >= 500:
            explanation = (
                "Read-heavy traffic is modeled without a dedicated cache tier, so repeated dashboard, feed, search, or catalog reads "
                "will amplify origin and database load during peak periods."
            )
            recommendation = "Introduce Redis or an equivalent cache tier for hot reads, sessions, and request throttling state."
            return self._risk(
                title="Cache pressure from uncached hot reads",
                severity=RiskSeverity.high,
                category="cache_pressure",
                explanation=explanation,
                recommendation=recommendation,
                affected_components=["api-service", "postgres"],
                recommendations=[
                    recommendation,
                    "Cache the highest-volume GET endpoints with bounded TTLs.",
                ],
            )

        if cache_nodes and scenario.peak_rps >= 1_500:
            explanation = (
                "A single cache tier is present, but the modeled read rate is high enough that hot keys, session concentration, or rate-limit counters "
                "can create cache saturation and cascading origin fallbacks."
            )
            recommendation = "Shard hot keys, monitor eviction and saturation rates, and separate session or counter workloads from bulk read caching."
            return self._risk(
                title="Cache pressure on hot keys",
                severity=RiskSeverity.medium,
                category="cache_pressure",
                explanation=explanation,
                recommendation=recommendation,
                affected_components=[node.id for node in cache_nodes],
                recommendations=[
                    recommendation,
                    "Set explicit memory policies and alert on cache hit-rate drops.",
                ],
            )

        return None

    def _queue_lag_risk(
        self,
        architecture: ArchitectureSpec,
        scenario: LoadScenario,
        node_kinds: set[ComponentKind],
    ) -> RiskItem | None:
        if not scenario.background_worker_traffic:
            return None

        peak_jobs_per_minute = sum(worker.peak_jobs_per_minute for worker in scenario.background_worker_traffic)
        worker_count = max(1, scenario.concurrency_levels.background_workers)
        jobs_per_worker = peak_jobs_per_minute / worker_count
        has_queue = ComponentKind.queue in node_kinds

        if not has_queue:
            explanation = (
                "Background jobs are modeled in the load profile, but the architecture does not include a queue tier to buffer spikes and retries."
            )
            recommendation = "Introduce a durable queue with backlog, retry, and dead-letter monitoring before relying on worker-driven workflows."
            return self._risk(
                title="Queue lag risk from missing queue tier",
                severity=RiskSeverity.high,
                category="queue_lag_risk",
                explanation=explanation,
                recommendation=recommendation,
                affected_components=["worker", "api-service"],
                recommendations=[
                    recommendation,
                    "Scale workers on queue age and processing latency, not only API traffic.",
                ],
            )

        if jobs_per_worker >= 500:
            explanation = (
                "Peak background job volume per worker is high relative to the modeled worker pool, which makes queue age, retries, and downstream saturation likely during spikes."
            )
            recommendation = "Increase worker capacity, cap per-job fanout, and autoscale workers using queue age and backlog thresholds."
            return self._risk(
                title="Queue lag risk under bursty worker load",
                severity=RiskSeverity.high if jobs_per_worker >= 1_000 else RiskSeverity.medium,
                category="queue_lag_risk",
                explanation=explanation,
                recommendation=recommendation,
                affected_components=[node.id for node in architecture.queues] + ["worker"],
                recommendations=[
                    recommendation,
                    "Use dead-letter queues and idempotent consumers for recovery from backlog spikes.",
                ],
            )

        return None

    def _hot_partition_risk(
        self,
        requirement: StructuredRequirementSpec,
        architecture: ArchitectureSpec,
        scenario: LoadScenario,
    ) -> RiskItem | None:
        scenario_type = scenario.scenario_type
        concentrated_write = any(item.percentage >= 25 and item.method != "GET" for item in (scenario.endpoint_request_mix or scenario.request_mix))
        if scenario_type not in {
            LoadScenarioType.chat_app,
            LoadScenarioType.ecommerce_flash_sale,
            LoadScenarioType.video_platform,
        } and not concentrated_write:
            return None

        if scenario_type == LoadScenarioType.ecommerce_flash_sale:
            explanation = (
                "Flash-sale traffic tends to collapse onto a small set of hot products, carts, and inventory rows, which can create partition or row-level contention even when overall throughput looks acceptable."
            )
        elif scenario_type == LoadScenarioType.chat_app:
            explanation = (
                "Large rooms or popular conversations can concentrate writes and reads on a narrow set of conversation identifiers, creating hot partitions in message storage or fanout queues."
            )
        else:
            explanation = (
                "Highly skewed content popularity can drive the majority of traffic through a small set of keys, partitions, or recommendation entities, causing uneven saturation."
            )

        recommendation = "Introduce partition-aware keys, per-tenant or per-room sharding, and queue or storage designs that avoid concentrating all hot traffic on one logical key range."
        return self._risk(
            title="Hot partition risk",
            severity=RiskSeverity.high if scenario.peak_rps >= 1_000 else RiskSeverity.medium,
            category="hot_partitions",
            explanation=explanation,
            recommendation=recommendation,
            affected_components=[node.id for node in architecture.databases] or ["postgres"],
            recommendations=[
                recommendation,
                "Load test skewed keys explicitly instead of only using evenly distributed synthetic traffic.",
            ],
        )

    def _single_region_risk(
        self,
        requirement: StructuredRequirementSpec,
        architecture: ArchitectureSpec,
    ) -> RiskItem | None:
        multi_region_needed = len(requirement.traffic.regions) > 1 or requirement.availability_target in {"99.95%", "99.99%"}
        if not multi_region_needed:
            return None

        failover_text = " ".join(architecture.failover_strategy + architecture.availability_strategy).lower()
        if any(keyword in failover_text for keyword in ("regional", "multi-region", "another healthy region", "traffic steering")):
            return None

        explanation = (
            "The traffic and availability requirements imply cross-region resilience, but the documented failover strategy remains limited to in-region redundancy."
        )
        recommendation = "Add regional traffic steering, replicated stateful recovery paths, and tested regional failover procedures for critical user journeys."
        return self._risk(
            title="Single-region risk",
            severity=RiskSeverity.high,
            category="single_region_risk",
            explanation=explanation,
            recommendation=recommendation,
            affected_components=[node.id for node in architecture.nodes if node.stateful] or ["load-balancer"],
            recommendations=[
                recommendation,
                "Document which workflows can degrade gracefully if a full multi-region architecture is deferred.",
            ],
        )

    def _autoscaling_gap_risk(self, architecture: ArchitectureSpec, scenario: LoadScenario) -> RiskItem | None:
        scaling_text = " ".join(architecture.scaling_strategy + architecture.scaling_notes).lower()
        missing_autoscale = not any(keyword in scaling_text for keyword in ("autoscale", "auto scale", "horizontal", "queue backlog"))
        if not missing_autoscale and scenario.concurrency_levels.peak_users < 2_000:
            return None

        explanation = (
            "The modeled traffic includes meaningful concurrency growth, but the architecture does not clearly define autoscaling triggers for APIs, workers, caches, and other shared dependencies."
        )
        recommendation = "Define autoscaling policies tied to latency, CPU, queue age, and saturation signals rather than relying on static instance counts."
        return self._risk(
            title="Autoscaling gap",
            severity=RiskSeverity.high if scenario.concurrency_levels.peak_users >= 4_000 else RiskSeverity.medium,
            category="autoscaling_gap",
            explanation=explanation,
            recommendation=recommendation,
            affected_components=[node.id for node in architecture.services] or ["api-service"],
            recommendations=[
                recommendation,
                "Exercise scale-up and scale-down behavior during load tests instead of only measuring steady-state capacity.",
            ],
        )

    def _cost_hotspot_risk(
        self,
        requirement: StructuredRequirementSpec,
        architecture: ArchitectureSpec,
        scenario: LoadScenario,
    ) -> RiskItem | None:
        storage_ids = {node.id for node in architecture.storage}
        worker_cost = sum(worker.peak_jobs_per_minute for worker in scenario.background_worker_traffic)
        high_egress_pattern = scenario.scenario_type == LoadScenarioType.video_platform and "cdn" not in storage_ids
        heavy_async_cost = worker_cost >= 5_000
        expensive_observability = len(architecture.observability) > 0 and scenario.peak_rps >= 2_000

        if not any((high_egress_pattern, heavy_async_cost, expensive_observability)):
            return None

        reasons: list[str] = []
        if high_egress_pattern:
            reasons.append("video or media traffic is modeled without a CDN, which pushes egress and origin serving costs onto core infrastructure")
        if heavy_async_cost:
            reasons.append("background job volume is high enough that worker fleets, queue throughput, and downstream calls can dominate runtime spend")
        if expensive_observability:
            reasons.append("high request volume with full telemetry collection can create outsized log, metrics, and trace ingestion costs")

        explanation = "Cost hotspots are likely because " + "; ".join(reasons) + "."
        recommendation = "Set cost budgets for CDN, worker, and observability workloads, and tune sampling, retention, and offload paths before peak launches."
        return self._risk(
            title="Cost hotspot risk",
            severity=RiskSeverity.medium,
            category="cost_hotspots",
            explanation=explanation,
            recommendation=recommendation,
            affected_components=[node.id for node in architecture.storage + architecture.observability] or ["worker"],
            recommendations=[
                recommendation,
                "Measure unit economics per request, per export, or per streamed minute so scaling decisions include cost signals.",
            ],
        )

    def _primary_scenario(self, load_profile: LoadProfileSpec, requirement: StructuredRequirementSpec) -> LoadScenario:
        return max(load_profile.scenarios, key=lambda item: item.peak_rps)

    def _request_percentage(self, scenario: LoadScenario, methods: set[str]) -> int:
        request_mix = scenario.endpoint_request_mix or scenario.request_mix
        return sum(item.percentage for item in request_mix if item.method.upper() in methods)

    def _risk(
        self,
        *,
        title: str,
        severity: RiskSeverity,
        category: str,
        explanation: str,
        recommendation: str,
        affected_components: list[str],
        recommendations: list[str],
    ) -> RiskItem:
        return RiskItem(
            title=title,
            severity=severity,
            category=category,
            explanation=explanation,
            recommendation=recommendation,
            description=explanation,
            affected_components=affected_components,
            rationale=explanation,
            recommendations=self._unique_lines([recommendation, *recommendations]),
        )

    def _severity_rank(self, risk: RiskItem) -> int:
        order = {
            RiskSeverity.critical: 0,
            RiskSeverity.high: 1,
            RiskSeverity.medium: 2,
            RiskSeverity.low: 3,
        }
        return order[risk.severity]

    def _unique_lines(self, values: Iterable[str]) -> list[str]:
        unique: list[str] = []
        for value in values:
            if value not in unique:
                unique.append(value)
        return unique
