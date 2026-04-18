from app.schemas.architecture import ArchitectureEdge, ArchitectureNode, ArchitectureSpec, ComponentKind
from app.schemas.load_profile import (
    BackgroundWorkerTraffic,
    ConcurrencyLevels,
    LoadProfileSpec,
    LoadScenario,
    LoadScenarioType,
    RequestMixItem,
    TrafficPattern,
    TrafficWindow,
)
from app.schemas.requirement import StructuredRequirementSpec, TrafficExpectation
from app.services.risks.risk_analyzer import RiskAnalyzer


def test_risk_analyzer_identifies_requested_risk_categories() -> None:
    requirement = StructuredRequirementSpec(
        product_name="Flash Global Shop",
        summary="Global e-commerce flash sale with hot inventory, checkout spikes, and asynchronous receipt processing.",
        client_surfaces=["web"],
        traffic=TrafficExpectation(
            baseline_rps=500,
            peak_rps=3000,
            peak_concurrency=9000,
            regions=["us-east-1", "eu-west-1"],
        ),
        availability_target="99.99%",
    )
    architecture = ArchitectureSpec(
        overview="Minimal architecture",
        nodes=[
            ArchitectureNode(
                id="load-balancer",
                name="Load Balancer",
                kind=ComponentKind.load_balancer,
                technology="ALB",
                description="Routes traffic.",
            ),
            ArchitectureNode(
                id="api-service",
                name="API Service",
                kind=ComponentKind.service,
                technology="FastAPI",
                description="Handles traffic.",
            ),
            ArchitectureNode(
                id="postgres",
                name="Database",
                kind=ComponentKind.database,
                technology="PostgreSQL",
                description="Stores data.",
                stateful=True,
            ),
            ArchitectureNode(
                id="observability-stack",
                name="Observability",
                kind=ComponentKind.observability,
                technology="Metrics and logs",
                description="Collects telemetry.",
                stateful=True,
            ),
        ],
        edges=[
            ArchitectureEdge(
                source="load-balancer",
                target="api-service",
                interaction="Routes requests",
                protocol="HTTPS",
                critical_path=True,
            ),
            ArchitectureEdge(
                source="api-service",
                target="postgres",
                interaction="Reads and writes data",
                protocol="SQL",
                critical_path=True,
            ),
        ],
        availability_strategy=["Use a load balancer at the edge."],
        observability=[
            ArchitectureNode(
                id="observability-stack",
                name="Observability",
                kind=ComponentKind.observability,
                technology="Metrics and logs",
                description="Collects telemetry.",
                stateful=True,
            )
        ],
    )
    load_profile = LoadProfileSpec(
        objective="Stress peak load.",
        scenarios=[
            LoadScenario(
                name="Peak",
                description="Flash sale peak",
                scenario_type=LoadScenarioType.ecommerce_flash_sale,
                traffic_pattern=TrafficPattern.spiky,
                duration_minutes=30,
                steady_state_rps=500,
                peak_rps=3000,
                concurrency=9000,
                think_time_seconds=0.8,
                baseline_traffic=TrafficWindow(rps=500, requests_per_minute=30000, description="Baseline traffic."),
                concurrency_levels=ConcurrencyLevels(
                    baseline_users=2500,
                    target_users=6000,
                    peak_users=9000,
                    background_workers=4,
                ),
                request_mix=[
                    RequestMixItem(name="Catalog browse", method="GET", path="/api/products", percentage=40),
                    RequestMixItem(name="Product detail", method="GET", path="/api/products/{id}", percentage=20),
                    RequestMixItem(name="Checkout", method="POST", path="/api/checkout", percentage=25),
                    RequestMixItem(name="Payment confirm", method="POST", path="/api/payments/confirm", percentage=15),
                ],
                endpoint_request_mix=[
                    RequestMixItem(name="Catalog browse", method="GET", path="/api/products", percentage=40),
                    RequestMixItem(name="Product detail", method="GET", path="/api/products/{id}", percentage=20),
                    RequestMixItem(name="Checkout", method="POST", path="/api/checkout", percentage=25),
                    RequestMixItem(name="Payment confirm", method="POST", path="/api/payments/confirm", percentage=15),
                ],
                background_worker_traffic=[
                    BackgroundWorkerTraffic(
                        name="Receipt pipeline",
                        queue_name="order-post-processing",
                        job_type="receipt_and_fraud",
                        steady_jobs_per_minute=3000,
                        peak_jobs_per_minute=12000,
                        trigger_sources=["/api/payments/confirm"],
                    )
                ],
            )
        ],
    )

    report = RiskAnalyzer().analyze(requirement=requirement, architecture=architecture, load_profile=load_profile)

    categories = {risk.category for risk in report.top_risks}
    assert {
        "database_bottleneck",
        "cache_pressure",
        "queue_lag_risk",
        "hot_partitions",
        "single_region_risk",
        "autoscaling_gap",
        "cost_hotspots",
    }.issubset(categories)
    assert all(risk.explanation for risk in report.top_risks)
    assert all(risk.recommendation for risk in report.top_risks)
    assert report.scaling_actions


def test_risk_analyzer_keeps_explicit_explanation_and_recommendation_fields() -> None:
    requirement = StructuredRequirementSpec(
        product_name="Analytics App",
        summary="Users upload reports and generate exports globally.",
        client_surfaces=["web"],
        traffic=TrafficExpectation(
            baseline_rps=400,
            peak_rps=2500,
            peak_concurrency=8000,
            regions=["us-east-1", "eu-west-1"],
        ),
        availability_target="99.99%",
    )
    architecture = ArchitectureSpec(
        overview="Minimal architecture",
        nodes=[
            ArchitectureNode(
                id="load-balancer",
                name="Load Balancer",
                kind=ComponentKind.load_balancer,
                technology="ALB",
                description="Routes traffic.",
            ),
            ArchitectureNode(
                id="api-service",
                name="API Service",
                kind=ComponentKind.service,
                technology="FastAPI",
                description="Handles traffic.",
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
        edges=[
            ArchitectureEdge(
                source="load-balancer",
                target="api-service",
                interaction="Routes requests",
                protocol="HTTPS",
                critical_path=True,
            ),
            ArchitectureEdge(
                source="api-service",
                target="postgres",
                interaction="Reads and writes data",
                protocol="SQL",
                critical_path=True,
            ),
        ],
        availability_strategy=["Use a load balancer at the edge."],
    )
    load_profile = LoadProfileSpec(
        objective="Stress peak load.",
        scenarios=[
            LoadScenario(
                name="Peak",
                description="Peak stress",
                traffic_pattern=TrafficPattern.spiky,
                duration_minutes=30,
                steady_state_rps=400,
                peak_rps=2500,
                concurrency=8000,
                think_time_seconds=1.0,
                request_mix=[RequestMixItem(name="Upload", method="POST", path="/api/uploads", percentage=100)],
            )
        ],
    )

    report = RiskAnalyzer().analyze(requirement=requirement, architecture=architecture, load_profile=load_profile)

    assert report.top_risks
    assert report.top_risks[0].severity.value in {"critical", "high"}
    assert any("database" in risk.category for risk in report.top_risks)
    assert all(risk.explanation == risk.description for risk in report.top_risks)
    assert all(risk.recommendation in risk.recommendations for risk in report.top_risks)
