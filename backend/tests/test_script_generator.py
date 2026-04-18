from app.schemas.architecture import ArchitectureEdge, ArchitectureNode, ArchitectureSpec, ComponentKind
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
from app.schemas.script import ScriptTarget
from app.services.scripts.script_generator import ScriptGenerator


def build_architecture() -> ArchitectureSpec:
    return ArchitectureSpec(
        overview="Test architecture",
        nodes=[
            ArchitectureNode(
                id="load-balancer",
                name="Public Load Balancer",
                kind=ComponentKind.load_balancer,
                technology="ALB",
                description="Routes traffic.",
            ),
            ArchitectureNode(
                id="api-service",
                name="API Service",
                kind=ComponentKind.service,
                technology="FastAPI",
                description="Handles requests.",
            ),
            ArchitectureNode(
                id="postgres",
                name="Database",
                kind=ComponentKind.database,
                technology="PostgreSQL",
                description="Stores data.",
                stateful=True,
            ),
        ],
        services=[
            ArchitectureNode(
                id="api-service",
                name="API Service",
                kind=ComponentKind.service,
                technology="FastAPI",
                description="Handles requests.",
            )
        ],
        edges=[
            ArchitectureEdge(
                source="api-service",
                target="postgres",
                interaction="Reads and writes data",
                protocol="SQL",
                critical_path=True,
            )
        ],
    )


def build_load_profile() -> LoadProfileSpec:
    return LoadProfileSpec(
        objective="Validate baseline traffic.",
        scenarios=[
            LoadScenario(
                name="Primary",
                description="Primary scenario",
                scenario_type=LoadScenarioType.saas_dashboard,
                traffic_pattern=TrafficPattern.diurnal,
                duration_minutes=30,
                steady_state_rps=100,
                peak_rps=300,
                concurrency=500,
                think_time_seconds=1.2,
                baseline_traffic=TrafficWindow(rps=100, requests_per_minute=6000, description="Baseline traffic."),
                spike_traffic=SpikeTraffic(
                    name="Morning refresh",
                    trigger="Executives refresh dashboards",
                    peak_rps=300,
                    peak_concurrency=500,
                    duration_minutes=10,
                    recovery_minutes=15,
                ),
                concurrency_levels=ConcurrencyLevels(
                    baseline_users=150,
                    target_users=350,
                    peak_users=500,
                    background_workers=4,
                ),
                request_mix=[
                    RequestMixItem(name="Dashboard", method="GET", path="/api/dashboards/{id}", percentage=70),
                    RequestMixItem(name="Export", method="POST", path="/api/reports/export", percentage=30),
                ],
                endpoint_request_mix=[
                    RequestMixItem(name="Dashboard", method="GET", path="/api/dashboards/{id}", percentage=70),
                    RequestMixItem(name="Export", method="POST", path="/api/reports/export", percentage=30),
                ],
                ramp_up=[
                    RampStage(duration_minutes=10, target_rps=100, target_concurrency=250),
                    RampStage(duration_minutes=20, target_rps=300, target_concurrency=500),
                ],
                ramp_up_stages=[
                    RampStage(duration_minutes=10, target_rps=100, target_concurrency=250),
                    RampStage(duration_minutes=20, target_rps=300, target_concurrency=500),
                ],
                spikes=[SpikeProfile(name="Morning refresh", peak_multiplier=3.0, duration_minutes=10, recovery_minutes=15)],
                user_journeys=[
                    UserJourney(
                        name="Analyst exploration",
                        persona="analyst",
                        percentage=70,
                        steps=[
                            UserJourneyStep(
                                name="Dashboard load",
                                method="GET",
                                path="/api/dashboards/{id}",
                                description="Open dashboard.",
                            ),
                            UserJourneyStep(
                                name="Export report",
                                method="POST",
                                path="/api/reports/export",
                                description="Trigger export.",
                            ),
                        ],
                    )
                ],
                background_worker_traffic=[
                    BackgroundWorkerTraffic(
                        name="Report export pipeline",
                        queue_name="report-exports",
                        job_type="report_export",
                        steady_jobs_per_minute=120,
                        peak_jobs_per_minute=400,
                        trigger_sources=["/api/reports/export"],
                    )
                ],
            )
        ],
    )


def test_script_generator_exports_k6_and_locust() -> None:
    generator = ScriptGenerator()
    architecture = build_architecture()
    load_profile = build_load_profile()

    k6_script = generator.generate(architecture=architecture, load_profile=load_profile, target=ScriptTarget.k6)
    locust_script = generator.generate(architecture=architecture, load_profile=load_profile, target=ScriptTarget.locust)

    assert "k6/http" in k6_script.content
    assert "export const options" in k6_script.content
    assert "stages:" in k6_script.content
    assert "check(response" in k6_script.content
    assert "sleep(" in k6_script.content
    assert "ScaleCraft generated k6 script" in k6_script.content
    assert "/api/dashboards/{id}" in k6_script.content
    assert "Report export pipeline" in k6_script.content

    assert "class ScaleCraftUser(HttpUser)" in locust_script.content
    assert "class StagedLoadShape(LoadTestShape)" in locust_script.content
    assert "class BackgroundWorkerTriggerUser(HttpUser)" in locust_script.content
    assert "@task(70)" in locust_script.content
    assert "catch_response=True" in locust_script.content
    assert "response.failure" in locust_script.content
    assert "ScaleCraft generated Locust file" in locust_script.content
