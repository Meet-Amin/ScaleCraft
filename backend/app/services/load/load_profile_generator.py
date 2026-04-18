from app.schemas.load_profile import (
    BackgroundWorkerTraffic,
    ConcurrencyLevels,
    LoadProfileSpec,
    LoadScenario,
    LoadScenarioType,
    RampStage,
    RequestMixItem,
    SpikeProfile,
    SpikeTraffic,
    TrafficPattern,
    TrafficWindow,
    UserJourney,
    UserJourneyStep,
)
from app.schemas.requirement import StructuredRequirementSpec


class LoadProfileGenerator:
    def generate(self, requirement: StructuredRequirementSpec) -> LoadProfileSpec:
        scenario_type = self._detect_scenario_type(requirement)
        primary_scenario = self._build_primary_scenario(requirement, scenario_type)
        scenarios = [primary_scenario]

        if primary_scenario.spike_traffic is not None and self._needs_peak_event_scenario(primary_scenario):
            scenarios.append(self._build_peak_event_scenario(primary_scenario))

        return LoadProfileSpec(
            objective=(
                f"Validate that {requirement.product_name} sustains baseline traffic, peak events, and "
                "background job load with enough headroom for scaling decisions."
            ),
            scenarios=scenarios,
            kpis=self._build_kpis(requirement, primary_scenario),
            global_assumptions=self._build_global_assumptions(requirement, primary_scenario),
        )

    def _build_primary_scenario(
        self,
        requirement: StructuredRequirementSpec,
        scenario_type: LoadScenarioType,
    ) -> LoadScenario:
        baseline_rps = requirement.traffic.baseline_rps
        peak_rps = max(requirement.traffic.peak_rps, baseline_rps)
        peak_concurrency = max(requirement.traffic.peak_concurrency, peak_rps)
        request_mix = self._normalize_mix(self._build_request_mix(scenario_type))
        user_journeys = self._build_user_journeys(scenario_type)
        background_worker_traffic = self._build_background_worker_traffic(scenario_type, baseline_rps, peak_rps)
        concurrency_levels = self._build_concurrency_levels(peak_concurrency, background_worker_traffic)
        traffic_pattern = self._infer_pattern(requirement, scenario_type)
        ramp_up = self._build_ramp_plan(
            baseline_rps=baseline_rps,
            peak_rps=peak_rps,
            target_concurrency=concurrency_levels.target_users,
            peak_concurrency=concurrency_levels.peak_users,
            scenario_type=scenario_type,
        )
        spike_traffic = self._build_spike_traffic(requirement, scenario_type, baseline_rps, peak_rps, peak_concurrency)
        spikes = []
        if spike_traffic is not None:
            spikes.append(
                SpikeProfile(
                    name=spike_traffic.name,
                    peak_multiplier=round(spike_traffic.peak_rps / max(1, baseline_rps), 2),
                    duration_minutes=spike_traffic.duration_minutes,
                    recovery_minutes=spike_traffic.recovery_minutes,
                )
            )

        return LoadScenario(
            name=self._scenario_name(scenario_type),
            description=self._scenario_description(scenario_type),
            scenario_type=scenario_type,
            traffic_pattern=traffic_pattern,
            duration_minutes=self._scenario_duration(scenario_type),
            steady_state_rps=baseline_rps,
            peak_rps=peak_rps,
            concurrency=concurrency_levels.peak_users,
            think_time_seconds=self._think_time_seconds(scenario_type),
            baseline_traffic=TrafficWindow(
                rps=baseline_rps,
                requests_per_minute=baseline_rps * 60,
                description="Expected steady-state user traffic during normal operation.",
            ),
            spike_traffic=spike_traffic,
            concurrency_levels=concurrency_levels,
            request_mix=request_mix,
            endpoint_request_mix=request_mix,
            ramp_up=ramp_up,
            ramp_up_stages=ramp_up,
            spikes=spikes,
            user_journeys=user_journeys,
            background_worker_traffic=background_worker_traffic,
            assumptions=self._build_scenario_assumptions(requirement, scenario_type, background_worker_traffic),
        )

    def _build_peak_event_scenario(self, primary_scenario: LoadScenario) -> LoadScenario:
        spike_traffic = primary_scenario.spike_traffic
        if spike_traffic is None:
            return primary_scenario

        peak_concurrency = max(primary_scenario.concurrency_levels.peak_users, spike_traffic.peak_concurrency)
        concurrency_levels = primary_scenario.concurrency_levels.model_copy(
            update={
                "target_users": max(primary_scenario.concurrency_levels.target_users, int(peak_concurrency * 0.8)),
                "peak_users": peak_concurrency,
            }
        )
        ramp_up = [
            RampStage(
                duration_minutes=5,
                target_rps=max(primary_scenario.steady_state_rps, int(spike_traffic.peak_rps * 0.5)),
                target_concurrency=max(primary_scenario.concurrency_levels.target_users, int(peak_concurrency * 0.6)),
            ),
            RampStage(
                duration_minutes=5,
                target_rps=max(primary_scenario.peak_rps, int(spike_traffic.peak_rps * 0.8)),
                target_concurrency=max(primary_scenario.concurrency_levels.target_users, int(peak_concurrency * 0.8)),
            ),
            RampStage(
                duration_minutes=spike_traffic.duration_minutes,
                target_rps=spike_traffic.peak_rps,
                target_concurrency=peak_concurrency,
            ),
        ]

        return primary_scenario.model_copy(
            update={
                "name": f"{primary_scenario.name} Peak Event",
                "description": "Stress scenario focused on peak arrival bursts, queue buildup, and recovery behavior.",
                "traffic_pattern": TrafficPattern.spiky,
                "duration_minutes": spike_traffic.duration_minutes + spike_traffic.recovery_minutes + 10,
                "peak_rps": spike_traffic.peak_rps,
                "concurrency": peak_concurrency,
                "think_time_seconds": max(0.2, primary_scenario.think_time_seconds * 0.65),
                "concurrency_levels": concurrency_levels,
                "ramp_up": ramp_up,
                "ramp_up_stages": ramp_up,
                "assumptions": primary_scenario.assumptions
                + ["Peak-event scenario prioritizes saturation and recovery over perfect user realism."],
            }
        )

    def _detect_scenario_type(self, requirement: StructuredRequirementSpec) -> LoadScenarioType:
        text = self._requirement_text(requirement)
        if any(keyword in text for keyword in ("chat", "message", "dm", "conversation", "room", "realtime")):
            return LoadScenarioType.chat_app
        if any(keyword in text for keyword in ("flash sale", "checkout", "cart", "order", "inventory", "catalog")):
            return LoadScenarioType.ecommerce_flash_sale
        if any(keyword in text for keyword in ("video", "stream", "playback", "creator", "watch", "media")):
            return LoadScenarioType.video_platform
        if any(keyword in text for keyword in ("dashboard", "analytics", "workspace", "report", "saas", "tenant")):
            return LoadScenarioType.saas_dashboard
        return LoadScenarioType.generic

    def _build_request_mix(self, scenario_type: LoadScenarioType) -> list[RequestMixItem]:
        mix_by_type = {
            LoadScenarioType.chat_app: [
                RequestMixItem(name="Conversation list", method="GET", path="/api/conversations", percentage=20),
                RequestMixItem(name="Thread fetch", method="GET", path="/api/conversations/{id}/messages", percentage=25),
                RequestMixItem(name="Send message", method="POST", path="/api/messages", percentage=30),
                RequestMixItem(name="Presence heartbeat", method="POST", path="/api/presence/heartbeat", percentage=15),
                RequestMixItem(name="Notification sync", method="POST", path="/api/notifications/read", percentage=10),
            ],
            LoadScenarioType.ecommerce_flash_sale: [
                RequestMixItem(name="Catalog browse", method="GET", path="/api/products", percentage=25),
                RequestMixItem(name="Product detail", method="GET", path="/api/products/{id}", percentage=20),
                RequestMixItem(name="Add to cart", method="POST", path="/api/cart/items", percentage=15),
                RequestMixItem(name="Checkout", method="POST", path="/api/checkout", percentage=20),
                RequestMixItem(name="Payment confirm", method="POST", path="/api/payments/confirm", percentage=10),
                RequestMixItem(name="Order status", method="GET", path="/api/orders/{id}", percentage=10),
            ],
            LoadScenarioType.video_platform: [
                RequestMixItem(name="Home feed", method="GET", path="/api/feed", percentage=25),
                RequestMixItem(name="Video metadata", method="GET", path="/api/videos/{id}", percentage=20),
                RequestMixItem(name="Playback session", method="POST", path="/api/videos/{id}/playback-token", percentage=20),
                RequestMixItem(name="Search", method="GET", path="/api/search", percentage=15),
                RequestMixItem(name="Interaction", method="POST", path="/api/interactions/like", percentage=10),
                RequestMixItem(name="Upload", method="POST", path="/api/videos/upload", percentage=10),
            ],
            LoadScenarioType.saas_dashboard: [
                RequestMixItem(name="Session bootstrap", method="GET", path="/api/auth/session", percentage=10),
                RequestMixItem(name="Dashboard load", method="GET", path="/api/dashboards/{id}", percentage=30),
                RequestMixItem(name="Widget query", method="GET", path="/api/widgets/query", percentage=20),
                RequestMixItem(name="Reports list", method="GET", path="/api/reports", percentage=15),
                RequestMixItem(name="Export report", method="POST", path="/api/reports/export", percentage=15),
                RequestMixItem(name="Alert config", method="POST", path="/api/alerts/config", percentage=10),
            ],
            LoadScenarioType.generic: [
                RequestMixItem(name="Primary read", method="GET", path="/api/resources", percentage=60),
                RequestMixItem(name="Primary write", method="POST", path="/api/resources", percentage=30),
                RequestMixItem(name="Bootstrap", method="GET", path="/api/health", percentage=10),
            ],
        }
        return mix_by_type[scenario_type]

    def _build_user_journeys(self, scenario_type: LoadScenarioType) -> list[UserJourney]:
        journeys_by_type = {
            LoadScenarioType.chat_app: [
                UserJourney(
                    name="Active chatter",
                    persona="power user",
                    percentage=50,
                    steps=[
                        UserJourneyStep(name="Open inbox", method="GET", path="/api/conversations", description="Load recent conversation list."),
                        UserJourneyStep(name="Open thread", method="GET", path="/api/conversations/{id}/messages", description="Fetch the active thread."),
                        UserJourneyStep(name="Send message", method="POST", path="/api/messages", description="Post a new message to the thread."),
                    ],
                ),
                UserJourney(
                    name="Passive reader",
                    persona="casual user",
                    percentage=35,
                    steps=[
                        UserJourneyStep(name="Resume session", method="GET", path="/api/conversations", description="Load conversations after reconnect."),
                        UserJourneyStep(name="Read unread", method="GET", path="/api/conversations/{id}/messages", description="Read unread messages."),
                    ],
                ),
                UserJourney(
                    name="Reconnect and sync",
                    persona="mobile user",
                    percentage=15,
                    steps=[
                        UserJourneyStep(name="Heartbeat", method="POST", path="/api/presence/heartbeat", description="Re-establish online presence."),
                        UserJourneyStep(name="Mark notifications", method="POST", path="/api/notifications/read", description="Acknowledge delivered notifications."),
                    ],
                ),
            ],
            LoadScenarioType.ecommerce_flash_sale: [
                UserJourney(
                    name="Window shopper",
                    persona="browser",
                    percentage=35,
                    steps=[
                        UserJourneyStep(name="Browse catalog", method="GET", path="/api/products", description="Load featured and category pages."),
                        UserJourneyStep(name="Open product", method="GET", path="/api/products/{id}", description="Inspect details and price changes."),
                    ],
                ),
                UserJourney(
                    name="Flash buyer",
                    persona="high-intent buyer",
                    percentage=45,
                    steps=[
                        UserJourneyStep(name="Browse catalog", method="GET", path="/api/products", description="Find discounted inventory quickly."),
                        UserJourneyStep(name="Add to cart", method="POST", path="/api/cart/items", description="Reserve items in cart."),
                        UserJourneyStep(name="Checkout", method="POST", path="/api/checkout", description="Submit order during flash-sale contention."),
                        UserJourneyStep(name="Confirm payment", method="POST", path="/api/payments/confirm", description="Complete payment authorization."),
                    ],
                ),
                UserJourney(
                    name="Order tracker",
                    persona="returning buyer",
                    percentage=20,
                    steps=[
                        UserJourneyStep(name="Load order", method="GET", path="/api/orders/{id}", description="Check order and fulfillment status."),
                    ],
                ),
            ],
            LoadScenarioType.video_platform: [
                UserJourney(
                    name="Viewer binge",
                    persona="watcher",
                    percentage=55,
                    steps=[
                        UserJourneyStep(name="Load feed", method="GET", path="/api/feed", description="Load personalized feed."),
                        UserJourneyStep(name="Request playback", method="POST", path="/api/videos/{id}/playback-token", description="Start video playback session."),
                        UserJourneyStep(name="Load metadata", method="GET", path="/api/videos/{id}", description="Fetch metadata and engagement counters."),
                    ],
                ),
                UserJourney(
                    name="Searcher",
                    persona="intent-driven viewer",
                    percentage=25,
                    steps=[
                        UserJourneyStep(name="Search content", method="GET", path="/api/search", description="Search and filter relevant videos."),
                        UserJourneyStep(name="Open result", method="GET", path="/api/videos/{id}", description="Open a selected result."),
                    ],
                ),
                UserJourney(
                    name="Creator upload",
                    persona="creator",
                    percentage=20,
                    steps=[
                        UserJourneyStep(name="Upload video", method="POST", path="/api/videos/upload", description="Submit a new video upload."),
                        UserJourneyStep(name="Like or interact", method="POST", path="/api/interactions/like", description="Perform engagement actions after upload or viewing."),
                    ],
                ),
            ],
            LoadScenarioType.saas_dashboard: [
                UserJourney(
                    name="Analyst exploration",
                    persona="analyst",
                    percentage=50,
                    steps=[
                        UserJourneyStep(name="Resume session", method="GET", path="/api/auth/session", description="Rehydrate auth and tenant context."),
                        UserJourneyStep(name="Open dashboard", method="GET", path="/api/dashboards/{id}", description="Load dashboard shell and metadata."),
                        UserJourneyStep(name="Run widget query", method="GET", path="/api/widgets/query", description="Fetch time-series or tabular data."),
                    ],
                ),
                UserJourney(
                    name="Admin export",
                    persona="workspace admin",
                    percentage=25,
                    steps=[
                        UserJourneyStep(name="List reports", method="GET", path="/api/reports", description="Inspect available reports."),
                        UserJourneyStep(name="Export report", method="POST", path="/api/reports/export", description="Trigger async export generation."),
                    ],
                ),
                UserJourney(
                    name="Executive overview",
                    persona="light user",
                    percentage=25,
                    steps=[
                        UserJourneyStep(name="Open dashboard", method="GET", path="/api/dashboards/{id}", description="View summary dashboard."),
                        UserJourneyStep(name="Update alert", method="POST", path="/api/alerts/config", description="Adjust alert settings or notifications."),
                    ],
                ),
            ],
            LoadScenarioType.generic: [
                UserJourney(
                    name="Primary workflow",
                    persona="default user",
                    percentage=100,
                    steps=[
                        UserJourneyStep(name="Read resource", method="GET", path="/api/resources", description="Load primary resource data."),
                        UserJourneyStep(name="Write resource", method="POST", path="/api/resources", description="Submit a primary state-changing action."),
                    ],
                )
            ],
        }
        return journeys_by_type[scenario_type]

    def _build_background_worker_traffic(
        self,
        scenario_type: LoadScenarioType,
        baseline_rps: int,
        peak_rps: int,
    ) -> list[BackgroundWorkerTraffic]:
        baseline_jobs = max(5, baseline_rps // 3)
        peak_jobs = max(baseline_jobs, peak_rps // 2)
        worker_by_type = {
            LoadScenarioType.chat_app: [
                BackgroundWorkerTraffic(
                    name="Message fanout",
                    queue_name="message-delivery",
                    job_type="fanout",
                    steady_jobs_per_minute=baseline_jobs * 60,
                    peak_jobs_per_minute=peak_jobs * 60,
                    trigger_sources=["/api/messages"],
                ),
                BackgroundWorkerTraffic(
                    name="Push notifications",
                    queue_name="notification-dispatch",
                    job_type="push_notification",
                    steady_jobs_per_minute=max(60, baseline_jobs * 20),
                    peak_jobs_per_minute=max(120, peak_jobs * 20),
                    trigger_sources=["/api/messages", "/api/notifications/read"],
                ),
            ],
            LoadScenarioType.ecommerce_flash_sale: [
                BackgroundWorkerTraffic(
                    name="Inventory reservation sync",
                    queue_name="inventory-reservations",
                    job_type="inventory_sync",
                    steady_jobs_per_minute=baseline_jobs * 40,
                    peak_jobs_per_minute=peak_jobs * 50,
                    trigger_sources=["/api/cart/items", "/api/checkout"],
                ),
                BackgroundWorkerTraffic(
                    name="Receipt and fraud processing",
                    queue_name="order-post-processing",
                    job_type="receipt_and_fraud",
                    steady_jobs_per_minute=baseline_jobs * 25,
                    peak_jobs_per_minute=peak_jobs * 30,
                    trigger_sources=["/api/payments/confirm"],
                ),
            ],
            LoadScenarioType.video_platform: [
                BackgroundWorkerTraffic(
                    name="Transcoding jobs",
                    queue_name="video-transcoding",
                    job_type="transcoding",
                    steady_jobs_per_minute=max(30, baseline_jobs * 10),
                    peak_jobs_per_minute=max(60, peak_jobs * 12),
                    trigger_sources=["/api/videos/upload"],
                ),
                BackgroundWorkerTraffic(
                    name="Recommendation refresh",
                    queue_name="recommendation-refresh",
                    job_type="recommendation",
                    steady_jobs_per_minute=max(60, baseline_jobs * 20),
                    peak_jobs_per_minute=max(120, peak_jobs * 24),
                    trigger_sources=["/api/feed", "/api/interactions/like"],
                ),
            ],
            LoadScenarioType.saas_dashboard: [
                BackgroundWorkerTraffic(
                    name="Report export pipeline",
                    queue_name="report-exports",
                    job_type="report_export",
                    steady_jobs_per_minute=max(30, baseline_jobs * 8),
                    peak_jobs_per_minute=max(60, peak_jobs * 10),
                    trigger_sources=["/api/reports/export"],
                ),
                BackgroundWorkerTraffic(
                    name="Digest and alert delivery",
                    queue_name="alert-digests",
                    job_type="alert_delivery",
                    steady_jobs_per_minute=max(20, baseline_jobs * 6),
                    peak_jobs_per_minute=max(40, peak_jobs * 8),
                    trigger_sources=["/api/alerts/config"],
                ),
            ],
            LoadScenarioType.generic: [],
        }
        return worker_by_type[scenario_type]

    def _build_concurrency_levels(
        self,
        peak_concurrency: int,
        background_worker_traffic: list[BackgroundWorkerTraffic],
    ) -> ConcurrencyLevels:
        baseline_users = max(1, peak_concurrency // 3)
        target_users = max(baseline_users, int(peak_concurrency * 0.7))
        background_workers = 0
        if background_worker_traffic:
            background_workers = max(2, min(500, peak_concurrency // 150))

        return ConcurrencyLevels(
            baseline_users=baseline_users,
            target_users=target_users,
            peak_users=peak_concurrency,
            background_workers=background_workers,
        )

    def _build_ramp_plan(
        self,
        *,
        baseline_rps: int,
        peak_rps: int,
        target_concurrency: int,
        peak_concurrency: int,
        scenario_type: LoadScenarioType,
    ) -> list[RampStage]:
        warmup_minutes = 8 if scenario_type == LoadScenarioType.chat_app else 10
        return [
            RampStage(
                duration_minutes=warmup_minutes,
                target_rps=max(1, baseline_rps // 2),
                target_concurrency=max(1, target_concurrency // 2),
            ),
            RampStage(
                duration_minutes=15,
                target_rps=baseline_rps,
                target_concurrency=max(1, int(target_concurrency * 0.8)),
            ),
            RampStage(
                duration_minutes=15,
                target_rps=max(baseline_rps, int(peak_rps * 0.75)),
                target_concurrency=max(1, target_concurrency),
            ),
            RampStage(
                duration_minutes=20,
                target_rps=peak_rps,
                target_concurrency=peak_concurrency,
            ),
        ]

    def _build_spike_traffic(
        self,
        requirement: StructuredRequirementSpec,
        scenario_type: LoadScenarioType,
        baseline_rps: int,
        peak_rps: int,
        peak_concurrency: int,
    ) -> SpikeTraffic | None:
        should_spike = peak_rps > baseline_rps or scenario_type in {
            LoadScenarioType.chat_app,
            LoadScenarioType.ecommerce_flash_sale,
            LoadScenarioType.video_platform,
        }
        if not should_spike:
            return None

        trigger_by_type = {
            LoadScenarioType.chat_app: "Large group conversation and reconnect storm",
            LoadScenarioType.ecommerce_flash_sale: "Promotional drop or limited inventory flash sale",
            LoadScenarioType.video_platform: "Featured content release or viral creator upload",
            LoadScenarioType.saas_dashboard: "Scheduled reporting window or executive morning dashboard refresh",
            LoadScenarioType.generic: "Promotional event or onboarding spike",
        }
        duration_by_type = {
            LoadScenarioType.chat_app: 12,
            LoadScenarioType.ecommerce_flash_sale: 15,
            LoadScenarioType.video_platform: 20,
            LoadScenarioType.saas_dashboard: 10,
            LoadScenarioType.generic: 10,
        }
        recovery_by_type = {
            LoadScenarioType.chat_app: 10,
            LoadScenarioType.ecommerce_flash_sale: 20,
            LoadScenarioType.video_platform: 20,
            LoadScenarioType.saas_dashboard: 15,
            LoadScenarioType.generic: 15,
        }
        boosted_peak_rps = max(peak_rps, int(baseline_rps * self._spike_multiplier(scenario_type, requirement)))
        boosted_peak_concurrency = max(peak_concurrency, boosted_peak_rps * self._concurrency_multiplier(scenario_type))

        return SpikeTraffic(
            name="Peak traffic event",
            trigger=trigger_by_type[scenario_type],
            peak_rps=boosted_peak_rps,
            peak_concurrency=boosted_peak_concurrency,
            duration_minutes=duration_by_type[scenario_type],
            recovery_minutes=recovery_by_type[scenario_type],
        )

    def _needs_peak_event_scenario(self, scenario: LoadScenario) -> bool:
        if scenario.spike_traffic is None:
            return False
        return scenario.scenario_type in {
            LoadScenarioType.chat_app,
            LoadScenarioType.ecommerce_flash_sale,
            LoadScenarioType.video_platform,
        } or scenario.spike_traffic.peak_rps >= scenario.steady_state_rps * 3

    def _normalize_mix(self, mix: list[RequestMixItem]) -> list[RequestMixItem]:
        total = sum(item.percentage for item in mix)
        normalized: list[RequestMixItem] = []
        assigned = 0
        for index, item in enumerate(mix):
            if index == len(mix) - 1:
                percentage = 100 - assigned
            else:
                percentage = max(1, round(item.percentage * 100 / total))
                assigned += percentage
            normalized.append(item.model_copy(update={"percentage": percentage}))
        return normalized

    def _infer_pattern(self, requirement: StructuredRequirementSpec, scenario_type: LoadScenarioType) -> TrafficPattern:
        if scenario_type in {LoadScenarioType.chat_app, LoadScenarioType.ecommerce_flash_sale}:
            return TrafficPattern.spiky
        if scenario_type == LoadScenarioType.video_platform:
            return TrafficPattern.bursty
        if scenario_type == LoadScenarioType.saas_dashboard or len(requirement.traffic.regions) > 1:
            return TrafficPattern.diurnal
        return TrafficPattern.steady

    def _scenario_name(self, scenario_type: LoadScenarioType) -> str:
        names = {
            LoadScenarioType.chat_app: "Chat traffic profile",
            LoadScenarioType.ecommerce_flash_sale: "Flash-sale traffic profile",
            LoadScenarioType.video_platform: "Video platform traffic profile",
            LoadScenarioType.saas_dashboard: "Dashboard traffic profile",
            LoadScenarioType.generic: "Primary user traffic",
        }
        return names[scenario_type]

    def _scenario_description(self, scenario_type: LoadScenarioType) -> str:
        descriptions = {
            LoadScenarioType.chat_app: "Realtime messaging mix with frequent thread reads, message sends, and reconnect events.",
            LoadScenarioType.ecommerce_flash_sale: "High-intent browse-to-checkout traffic with concentrated purchase and inventory pressure.",
            LoadScenarioType.video_platform: "Playback-heavy traffic with feed reads, metadata fetches, uploads, and engagement events.",
            LoadScenarioType.saas_dashboard: "Dashboard and report traffic with read-heavy queries plus asynchronous export activity.",
            LoadScenarioType.generic: "Representative mix of steady-state reads and writes across primary application workflows.",
        }
        return descriptions[scenario_type]

    def _scenario_duration(self, scenario_type: LoadScenarioType) -> int:
        durations = {
            LoadScenarioType.chat_app: 45,
            LoadScenarioType.ecommerce_flash_sale: 40,
            LoadScenarioType.video_platform: 90,
            LoadScenarioType.saas_dashboard: 60,
            LoadScenarioType.generic: 60,
        }
        return durations[scenario_type]

    def _think_time_seconds(self, scenario_type: LoadScenarioType) -> float:
        think_times = {
            LoadScenarioType.chat_app: 0.5,
            LoadScenarioType.ecommerce_flash_sale: 0.8,
            LoadScenarioType.video_platform: 2.5,
            LoadScenarioType.saas_dashboard: 4.0,
            LoadScenarioType.generic: 1.5,
        }
        return think_times[scenario_type]

    def _build_scenario_assumptions(
        self,
        requirement: StructuredRequirementSpec,
        scenario_type: LoadScenarioType,
        background_worker_traffic: list[BackgroundWorkerTraffic],
    ) -> list[str]:
        assumptions = [
            "Traffic runs against production-like infrastructure with representative seed data.",
            "Authentication and tenant setup are completed before the scenario starts.",
        ]
        if background_worker_traffic:
            assumptions.append("Background workers and queues are enabled so asynchronous load is measured alongside API traffic.")
        if scenario_type == LoadScenarioType.chat_app:
            assumptions.append("WebSocket or realtime connection costs are approximated through high-frequency API interactions and reconnect behavior.")
        if scenario_type == LoadScenarioType.video_platform:
            assumptions.append("Media bytes are largely offloaded to CDN or object storage, so API traffic models control-plane load rather than raw streaming throughput.")
        if len(requirement.traffic.regions) > 1:
            assumptions.append("Regional user distribution follows a diurnal pattern across the declared regions.")
        return assumptions

    def _build_kpis(self, requirement: StructuredRequirementSpec, primary_scenario: LoadScenario) -> list[str]:
        kpis = [
            "p95 API latency below 500ms during baseline traffic.",
            "Error rate remains below 1% for critical user journeys.",
            "All ramp-up stages complete without sustained saturation or cascading retries.",
        ]
        if primary_scenario.background_worker_traffic:
            kpis.append("Background queue lag stays within one minute at both baseline and peak traffic levels.")
        if primary_scenario.spike_traffic is not None:
            kpis.append("The system returns to baseline latency and backlog levels within the modeled recovery window after a spike.")
        if len(requirement.traffic.regions) > 1:
            kpis.append("Regional latency variance stays within acceptable SLO bands during diurnal traffic shifts.")
        return kpis

    def _build_global_assumptions(
        self,
        requirement: StructuredRequirementSpec,
        primary_scenario: LoadScenario,
    ) -> list[str]:
        assumptions = list(requirement.assumptions)
        assumptions.append(f"Primary load archetype detected as {primary_scenario.scenario_type.value}.")
        if primary_scenario.background_worker_traffic:
            assumptions.append("Asynchronous worker capacity is part of the overall system throughput budget.")
        return self._unique_lines(assumptions)

    def _spike_multiplier(self, scenario_type: LoadScenarioType, requirement: StructuredRequirementSpec) -> float:
        summary = requirement.summary.lower()
        if "viral" in summary or "launch" in summary:
            return 6.0
        multipliers = {
            LoadScenarioType.chat_app: 3.5,
            LoadScenarioType.ecommerce_flash_sale: 6.0,
            LoadScenarioType.video_platform: 4.0,
            LoadScenarioType.saas_dashboard: 2.5,
            LoadScenarioType.generic: 3.0,
        }
        return multipliers[scenario_type]

    def _concurrency_multiplier(self, scenario_type: LoadScenarioType) -> int:
        multipliers = {
            LoadScenarioType.chat_app: 3,
            LoadScenarioType.ecommerce_flash_sale: 2,
            LoadScenarioType.video_platform: 2,
            LoadScenarioType.saas_dashboard: 2,
            LoadScenarioType.generic: 2,
        }
        return multipliers[scenario_type]

    def _requirement_text(self, requirement: StructuredRequirementSpec) -> str:
        details = [requirement.summary]
        details.extend(item.description for item in requirement.functional_requirements)
        details.extend(item.description for item in requirement.non_functional_requirements)
        return " ".join(details).lower()

    def _unique_lines(self, values: list[str]) -> list[str]:
        unique: list[str] = []
        for value in values:
            if value not in unique:
                unique.append(value)
        return unique
