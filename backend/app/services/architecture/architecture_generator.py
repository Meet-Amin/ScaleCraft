from app.schemas.architecture import (
    ArchitectureEdge,
    ArchitectureNode,
    ArchitectureSpec,
    ComponentKind,
)
from app.schemas.requirement import StructuredRequirementSpec
from app.services.architecture.graph_builder import GraphBuilder


class ArchitectureGenerator:
    def __init__(self) -> None:
        self._graph_builder = GraphBuilder()

    def generate(self, requirement: StructuredRequirementSpec) -> ArchitectureSpec:
        nodes: list[ArchitectureNode] = []
        edges: list[ArchitectureEdge] = []

        scaling_strategy = [
            "Keep request-serving services stateless and scale them horizontally behind a managed load balancer.",
            "Autoscale API and worker capacity using CPU, latency, and queue backlog rather than fixed instance counts.",
        ]
        failover_strategy = [
            "Deploy stateless components across at least two availability zones and keep health-based traffic shifting enabled.",
            "Use managed backups and tested failover procedures for every stateful dependency.",
        ]
        availability_strategy = [
            "Run synchronous request paths across multiple instances to avoid single-instance failure impact.",
            "Terminate traffic at a public load balancer and remove unhealthy instances automatically.",
        ]
        data_strategy = [
            "Persist transactional system-of-record data in PostgreSQL with point-in-time recovery.",
        ]
        scaling_notes: list[str] = []

        self._add_node(
            nodes,
            ArchitectureNode(
                id="load-balancer",
                name="Public Load Balancer",
                kind=ComponentKind.load_balancer,
                technology="Managed L7 Load Balancer",
                description="Distributes inbound traffic across healthy API instances.",
                responsibilities=["TLS termination", "traffic routing", "health-based traffic shifting"],
                scaling_notes=["Use managed elasticity and health checks instead of static capacity allocations."],
            ),
        )
        self._add_node(
            nodes,
            ArchitectureNode(
                id="api-service",
                name="API Service",
                kind=ComponentKind.service,
                technology="FastAPI",
                description="Primary synchronous application service that validates requests and executes domain logic.",
                responsibilities=["request validation", "orchestration", "business workflows"],
                scaling_notes=["Keep stateless so it can scale horizontally during spikes."],
            ),
        )
        self._add_node(
            nodes,
            ArchitectureNode(
                id="postgres",
                name="Primary Database",
                kind=ComponentKind.database,
                technology="PostgreSQL",
                description="Primary transactional datastore for relational system data.",
                responsibilities=["writes", "consistent reads", "transactional integrity"],
                scaling_notes=["Add pooling, indexing, and read replicas before large vertical scaling steps."],
                stateful=True,
            ),
        )

        self._add_edge(edges, "load-balancer", "api-service", "Routes client traffic", "HTTPS", True)
        self._add_edge(edges, "api-service", "postgres", "Reads and writes core data", "SQL", True)

        if self._needs_cache(requirement):
            self._add_node(
                nodes,
                ArchitectureNode(
                    id="redis",
                    name="Cache Layer",
                    kind=ComponentKind.cache,
                    technology="Redis",
                    description="Caches hot reads, session state, and transient coordination data.",
                    responsibilities=["low-latency reads", "session storage", "request throttling state"],
                    scaling_notes=["Use bounded TTLs and eviction policies to protect the database from repeated reads."],
                    stateful=True,
                ),
            )
            self._add_edge(edges, "api-service", "redis", "Reads and writes hot cached data", "RESP", False)
            scaling_strategy.append("Use Redis to offload repeated reads, session lookups, and throttling state from PostgreSQL.")
            scaling_notes.append("A cache tier reduces repeat-read load on the primary database during peak traffic.")

        worker_present = False
        if self._needs_async_processing(requirement):
            self._add_node(
                nodes,
                ArchitectureNode(
                    id="queue",
                    name="Async Queue",
                    kind=ComponentKind.queue,
                    technology="Managed Queue",
                    description="Buffers asynchronous or burstable workloads away from the synchronous request path.",
                    responsibilities=["durable buffering", "backpressure", "decoupling"],
                    scaling_notes=["Alert on queue age and dead-letter volume, not only message depth."],
                    stateful=True,
                ),
            )
            self._add_node(
                nodes,
                ArchitectureNode(
                    id="worker",
                    name="Background Worker",
                    kind=ComponentKind.worker,
                    technology="Python Worker",
                    description="Consumes queued jobs such as exports, notifications, indexing, and other long-running tasks.",
                    responsibilities=["background processing", "retries", "job execution"],
                    scaling_notes=["Scale worker pools on queue backlog and processing latency."],
                ),
            )
            self._add_edge(edges, "api-service", "queue", "Publishes asynchronous tasks", "AMQP", False)
            self._add_edge(edges, "queue", "worker", "Delivers jobs for execution", "AMQP", False)
            self._add_edge(edges, "worker", "postgres", "Persists asynchronous job results", "SQL", False)
            worker_present = True
            scaling_strategy.append("Scale worker pools independently from API instances to absorb bursty asynchronous workloads.")
            failover_strategy.append("Use durable queues, retry policies, and dead-letter handling so asynchronous work survives worker or instance failure.")
            scaling_notes.append("Queue-backed workers absorb burst traffic and reduce timeout pressure on the API path.")

        if self._needs_object_storage(requirement):
            self._add_node(
                nodes,
                ArchitectureNode(
                    id="object-storage",
                    name="Object Storage",
                    kind=ComponentKind.object_storage,
                    technology="S3-compatible storage",
                    description="Stores uploads, exports, media, and large binary objects outside the transactional database.",
                    responsibilities=["binary asset storage", "durable export storage"],
                    scaling_notes=["Keep large object traffic out of PostgreSQL and use signed URLs where appropriate."],
                    stateful=True,
                ),
            )
            storage_source = "worker" if worker_present else "api-service"
            self._add_edge(edges, storage_source, "object-storage", "Stores and retrieves assets", "HTTPS", False)
            scaling_strategy.append("Store large binary assets in object storage instead of the transactional database.")
            failover_strategy.append("Use cross-zone durable object storage and lifecycle policies for exported or uploaded assets.")

        if len(requirement.traffic.regions) > 1 or requirement.domain.value in {"media", "ecommerce"}:
            self._add_node(
                nodes,
                ArchitectureNode(
                    id="cdn",
                    name="Content Delivery Network",
                    kind=ComponentKind.cdn,
                    technology="Managed CDN",
                    description="Caches cacheable content closer to end users and reduces origin request volume.",
                    responsibilities=["edge caching", "static asset offload", "regional acceleration"],
                    scaling_notes=["Cache static assets and route cache misses back to the origin load balancer."],
                ),
            )
            self._add_edge(edges, "cdn", "load-balancer", "Forwards cache misses to origin", "HTTPS", False)
            scaling_strategy.append("Use a CDN to reduce origin load and lower global latency for static or cacheable responses.")
            if len(requirement.traffic.regions) > 1:
                failover_strategy.append("Prepare regional traffic steering so another healthy region can absorb traffic during a regional outage.")

        if self._needs_search(requirement):
            self._add_node(
                nodes,
                ArchitectureNode(
                    id="search",
                    name="Search Index",
                    kind=ComponentKind.search,
                    technology="OpenSearch-compatible cluster",
                    description="Handles search and faceted discovery workloads outside the transactional database.",
                    responsibilities=["search queries", "faceted filtering", "index maintenance"],
                    scaling_notes=["Keep search workloads isolated from transactional queries and update indexes asynchronously where possible."],
                    stateful=True,
                ),
            )
            self._add_edge(edges, "api-service", "search", "Executes search queries", "HTTPS", False)
            update_source = "worker" if worker_present else "api-service"
            self._add_edge(edges, update_source, "search", "Updates search index", "HTTPS", False)
            data_strategy.append("Keep search indexes separate from transactional data so browse and discovery traffic do not compete with core writes.")

        if self._needs_auth_service(requirement):
            self._add_node(
                nodes,
                ArchitectureNode(
                    id="auth-service",
                    name="Identity Service",
                    kind=ComponentKind.service,
                    technology="OIDC / OAuth 2.0 Provider",
                    description="Handles authentication, token issuance, and authorization context for protected workflows.",
                    responsibilities=["authentication", "authorization", "token management"],
                    scaling_notes=["Keep token verification cheap and cacheable to avoid auth-service hot spots."],
                ),
            )
            self._add_edge(edges, "api-service", "auth-service", "Validates tokens and user identity", "HTTPS", True)

        if requirement.traffic.peak_rps >= 1_000:
            self._add_node(
                nodes,
                ArchitectureNode(
                    id="postgres-replica",
                    name="Read Replica",
                    kind=ComponentKind.database,
                    technology="PostgreSQL Read Replica",
                    description="Read-optimized replica used to offload heavy query traffic from the primary database.",
                    responsibilities=["read scaling", "reporting reads", "query isolation"],
                    scaling_notes=["Route non-transactional and read-heavy workloads to replicas with stale-read tolerance."],
                    stateful=True,
                ),
            )
            self._add_edge(edges, "postgres", "postgres-replica", "Replicates transactional data", "Replication", False)
            scaling_strategy.append("Introduce read replicas and workload isolation before large peak events or onboarding jumps.")
            failover_strategy.append("Promote healthy replicas or managed standby instances during primary database failure scenarios.")
            data_strategy.append("Use read replicas for reporting and browse-heavy reads that do not require strict write consistency.")

        self._add_node(
            nodes,
            ArchitectureNode(
                id="observability-stack",
                name="Observability Stack",
                kind=ComponentKind.observability,
                technology="Metrics, Logs, and Traces",
                description="Collects metrics, structured logs, traces, and alerting signals for all major components.",
                responsibilities=["metrics", "centralized logging", "distributed tracing", "alerting"],
                scaling_notes=["Instrument all critical services and alert on latency, saturation, and queue age."],
                stateful=True,
            ),
        )
        self._add_edge(edges, "api-service", "observability-stack", "Emits application telemetry", "OTLP", False)
        self._add_edge(edges, "postgres", "observability-stack", "Exports database telemetry", "Metrics", False)
        if worker_present:
            self._add_edge(edges, "worker", "observability-stack", "Emits worker telemetry", "OTLP", False)
        scaling_strategy.append("Use metrics, tracing, and saturation alerts to scale before latency or error rate regressions become user-visible.")
        failover_strategy.append("Continuously monitor health, lag, and saturation so failover conditions are detected early and exercised regularly.")

        for integration in requirement.integrations:
            node_id = f"external-{integration.lower().replace(' ', '-')}"
            self._add_node(
                nodes,
                ArchitectureNode(
                    id=node_id,
                    name=integration,
                    kind=ComponentKind.external_api,
                    technology=integration,
                    description=f"External integration dependency for {integration}.",
                    responsibilities=["third-party API integration"],
                    scaling_notes=["Use retries, timeouts, circuit breakers, and rate limiting around external calls."],
                ),
            )
            integration_source = "worker" if worker_present else "api-service"
            self._add_edge(edges, integration_source, node_id, f"Calls {integration}", "HTTPS", False)
            failover_strategy.append(f"Degrade gracefully when {integration} is slow or unavailable instead of blocking the full request path.")

        grouped = self._group_nodes(nodes)
        overview = (
            f"Scalable distributed architecture for {requirement.product_name} with stateless request handling, "
            "stateful data services, and optional caching or asynchronous processing driven by structured traffic needs."
        )
        draft_architecture = ArchitectureSpec(
            overview=overview,
            nodes=nodes,
            edges=edges,
            services=grouped["services"],
            databases=grouped["databases"],
            cache=grouped["cache"],
            queues=grouped["queues"],
            storage=grouped["storage"],
            observability=grouped["observability"],
            availability_strategy=self._unique_lines(availability_strategy),
            scaling_strategy=self._unique_lines(scaling_strategy),
            failover_strategy=self._unique_lines(failover_strategy),
            data_strategy=self._unique_lines(data_strategy),
            scaling_notes=self._unique_lines(scaling_notes + scaling_strategy),
            assumptions=requirement.assumptions,
        )
        graph = self._graph_builder.build(draft_architecture)
        graph_json = self._graph_builder.serialize(graph)
        explanation = self._build_explanation(requirement, draft_architecture)

        return draft_architecture.model_copy(update={"graph_json": graph_json, "explanation": explanation})

    def _group_nodes(self, nodes: list[ArchitectureNode]) -> dict[str, list[ArchitectureNode]]:
        return {
            "services": [node for node in nodes if node.kind in {ComponentKind.load_balancer, ComponentKind.service, ComponentKind.worker}],
            "databases": [node for node in nodes if node.kind in {ComponentKind.database, ComponentKind.search}],
            "cache": [node for node in nodes if node.kind == ComponentKind.cache],
            "queues": [node for node in nodes if node.kind == ComponentKind.queue],
            "storage": [node for node in nodes if node.kind in {ComponentKind.object_storage, ComponentKind.cdn}],
            "observability": [node for node in nodes if node.kind == ComponentKind.observability],
        }

    def _build_explanation(self, requirement: StructuredRequirementSpec, architecture: ArchitectureSpec) -> str:
        storage_summary = "object storage" if architecture.storage else "direct transactional data paths"
        queue_summary = "background workers consume queue-backed jobs for bursty workflows" if architecture.queues else "all modeled workflows stay on the synchronous API path"
        cache_summary = "a cache layer protects the primary database from repeated reads" if architecture.cache else "the database serves all modeled reads directly"
        observability_summary = "an observability stack captures metrics, logs, and traces across critical components"

        return (
            f"Traffic for {requirement.product_name} enters through the public edge and is routed to stateless FastAPI instances behind a managed load balancer. "
            f"The API service persists authoritative data in PostgreSQL, while {cache_summary}. "
            f"For binary assets and exports, the design uses {storage_summary}, and {queue_summary}. "
            f"{observability_summary}. The scaling strategy emphasizes horizontal service scaling, workload isolation, caching, and read offload as traffic grows, "
            f"while the failover strategy focuses on multi-zone deployment, durable stateful services, and explicit recovery paths for database, queue, and regional failures."
        )

    def _add_node(self, nodes: list[ArchitectureNode], node: ArchitectureNode) -> None:
        if all(existing.id != node.id for existing in nodes):
            nodes.append(node)

    def _add_edge(
        self,
        edges: list[ArchitectureEdge],
        source: str,
        target: str,
        interaction: str,
        protocol: str,
        critical_path: bool,
    ) -> None:
        edge = ArchitectureEdge(
            source=source,
            target=target,
            interaction=interaction,
            protocol=protocol,
            critical_path=critical_path,
        )
        if all(existing.source != edge.source or existing.target != edge.target or existing.interaction != edge.interaction for existing in edges):
            edges.append(edge)

    def _unique_lines(self, values: list[str]) -> list[str]:
        unique: list[str] = []
        for value in values:
            if value not in unique:
                unique.append(value)
        return unique

    def _needs_cache(self, requirement: StructuredRequirementSpec) -> bool:
        text = self._requirement_text(requirement)
        return requirement.traffic.peak_rps >= 300 or any(
            keyword in text for keyword in ("catalog", "feed", "dashboard", "search", "browse", "discover")
        )

    def _needs_async_processing(self, requirement: StructuredRequirementSpec) -> bool:
        text = self._requirement_text(requirement)
        return requirement.traffic.peak_rps >= 500 or any(
            keyword in text for keyword in ("notification", "email", "upload", "report", "import", "export", "processing")
        )

    def _needs_object_storage(self, requirement: StructuredRequirementSpec) -> bool:
        text = self._requirement_text(requirement)
        return any(keyword in text for keyword in ("upload", "file", "image", "video", "media", "document", "export"))

    def _needs_search(self, requirement: StructuredRequirementSpec) -> bool:
        text = self._requirement_text(requirement)
        return any(keyword in text for keyword in ("search", "filter", "discover", "catalog", "browse"))

    def _needs_auth_service(self, requirement: StructuredRequirementSpec) -> bool:
        security_categories = {item.category.lower() for item in requirement.non_functional_requirements}
        text = self._requirement_text(requirement)
        return "security" in security_categories or any(keyword in text for keyword in ("login", "role", "permission", "auth", "admin"))

    def _requirement_text(self, requirement: StructuredRequirementSpec) -> str:
        details = [requirement.summary]
        details.extend(item.description for item in requirement.functional_requirements)
        details.extend(item.description for item in requirement.non_functional_requirements)
        return " ".join(details).lower()
