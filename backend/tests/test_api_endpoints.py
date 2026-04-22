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


def test_parse_endpoint_rejects_short_input() -> None:
    response = client.post("/parse", json={"requirement_text": "too short"})
    assert response.status_code == 422
