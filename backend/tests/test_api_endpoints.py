from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_end_to_end_api_flow() -> None:
    parse_response = client.post(
        "/parse",
        json={
            "requirement_text": (
                "Build a SaaS analytics platform where admins manage workspaces, users view dashboards, "
                "reports are exported asynchronously, email notifications are sent, and the system supports "
                "300 rps baseline with peak 1200 rps and 3000 concurrent users."
            )
        },
    )
    assert parse_response.status_code == 200
    parsed_requirement = parse_response.json()["requirement"]

    architecture_response = client.post("/architecture", json={"requirement": parsed_requirement})
    assert architecture_response.status_code == 200
    architecture = architecture_response.json()["architecture"]
    assert architecture["services"]
    assert architecture["databases"]
    assert architecture["observability"]
    assert architecture["scaling_strategy"]
    assert architecture["failover_strategy"]
    assert architecture["graph_json"]["nodes"]
    assert architecture["graph_json"]["edges"]
    assert architecture["graph_json"]["multigraph"] is True
    assert architecture["explanation"]

    load_profile_response = client.post("/load-profile", json={"requirement": parsed_requirement})
    assert load_profile_response.status_code == 200
    load_profile = load_profile_response.json()["load_profile"]
    assert load_profile["scenarios"]
    assert load_profile["scenarios"][0]["baseline_traffic"]
    assert load_profile["scenarios"][0]["concurrency_levels"]
    assert load_profile["scenarios"][0]["user_journeys"]
    assert load_profile["scenarios"][0]["endpoint_request_mix"]
    assert load_profile["scenarios"][0]["background_worker_traffic"]
    assert load_profile["scenarios"][0]["ramp_up_stages"]

    script_response = client.post(
        "/generate-script",
        json={
            "architecture": architecture,
            "load_profile": load_profile,
            "target": "k6",
        },
    )
    assert script_response.status_code == 200
    assert script_response.json()["script"]["target"] == "k6"

    risks_response = client.post(
        "/analyze-risks",
        json={
            "requirement": parsed_requirement,
            "architecture": architecture,
            "load_profile": load_profile,
        },
    )
    assert risks_response.status_code == 200
    assert "summary" in risks_response.json()["report"]
    assert risks_response.json()["report"]["top_risks"]
    assert risks_response.json()["report"]["top_risks"][0]["explanation"]
    assert risks_response.json()["report"]["top_risks"][0]["recommendation"]


def test_parse_endpoint_rejects_short_input() -> None:
    response = client.post("/parse", json={"requirement_text": "too short"})
    assert response.status_code == 422
