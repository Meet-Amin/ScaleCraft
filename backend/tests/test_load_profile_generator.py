import pytest

from app.schemas.load_profile import LoadScenarioType
from app.schemas.requirement import StructuredRequirementSpec, TrafficExpectation
from app.services.load.load_profile_generator import LoadProfileGenerator


def test_load_profile_generator_creates_flash_sale_profile() -> None:
    requirement = StructuredRequirementSpec(
        product_name="Launch Platform",
        summary="Build an e-commerce flash sale platform with checkout surges and viral traffic spikes.",
        client_surfaces=["web"],
        traffic=TrafficExpectation(baseline_rps=200, peak_rps=1200, peak_concurrency=3000),
    )

    profile = LoadProfileGenerator().generate(requirement)
    primary = profile.scenarios[0]

    assert primary.scenario_type == LoadScenarioType.ecommerce_flash_sale
    assert primary.baseline_traffic.rps == 200
    assert primary.spike_traffic is not None
    assert primary.concurrency_levels.peak_users == 3000
    assert primary.concurrency_levels.background_workers > 0
    assert sum(item.percentage for item in primary.request_mix) == 100
    assert primary.endpoint_request_mix == primary.request_mix
    assert primary.ramp_up_stages == primary.ramp_up
    assert primary.user_journeys
    assert primary.background_worker_traffic
    assert any(item.path == "/api/checkout" for item in primary.request_mix)
    assert any(journey.name == "Flash buyer" for journey in primary.user_journeys)
    assert any(worker.job_type == "inventory_sync" for worker in primary.background_worker_traffic)
    assert len(profile.scenarios) >= 2


@pytest.mark.parametrize(
    ("summary", "expected_type", "expected_path", "expected_job_type"),
    [
        (
            "Create a chat app where users join rooms, read messages, send messages, and reconnect frequently.",
            LoadScenarioType.chat_app,
            "/api/messages",
            "fanout",
        ),
        (
            "Build a video platform where users watch feeds, stream videos, search content, and creators upload media.",
            LoadScenarioType.video_platform,
            "/api/videos/{id}/playback-token",
            "transcoding",
        ),
        (
            "Create a SaaS dashboard for analysts with workspaces, dashboard queries, scheduled reports, and exports.",
            LoadScenarioType.saas_dashboard,
            "/api/dashboards/{id}",
            "report_export",
        ),
    ],
)
def test_load_profile_generator_supports_named_archetypes(
    summary: str,
    expected_type: LoadScenarioType,
    expected_path: str,
    expected_job_type: str,
) -> None:
    requirement = StructuredRequirementSpec(
        product_name="Scenario App",
        summary=summary,
        client_surfaces=["web"],
        traffic=TrafficExpectation(baseline_rps=150, peak_rps=700, peak_concurrency=1800),
    )

    profile = LoadProfileGenerator().generate(requirement)
    primary = profile.scenarios[0]

    assert primary.scenario_type == expected_type
    assert any(item.path == expected_path for item in primary.request_mix)
    assert any(worker.job_type == expected_job_type for worker in primary.background_worker_traffic)
    assert primary.user_journeys
    assert primary.baseline_traffic.requests_per_minute == primary.baseline_traffic.rps * 60
    assert any(kpi.startswith("p95 API latency") for kpi in profile.kpis)
