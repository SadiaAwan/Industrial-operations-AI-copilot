"""HTTP contract, validation, error, and OpenAPI tests."""

from fastapi.testclient import TestClient

from app.main import create_app
from tests.api_fakes import fake_services


def test_openapi_exposes_all_phase_8_operations() -> None:
    client = TestClient(create_app(services=fake_services()))

    document = client.get("/openapi.json").json()

    assert {
        "/api/v1/chat",
        "/api/v1/chat/stream",
        "/api/v1/machines/{machine_id}/status",
        "/api/v1/sessions/{session_id}",
        "/api/v1/actions/{action_id}/approve",
        "/api/v1/actions/{action_id}/reject",
        "/api/v1/feedback",
        "/health",
        "/ready",
    } <= document["paths"].keys()


def test_invalid_chat_request_returns_structured_error_and_correlation_id() -> None:
    client = TestClient(create_app(services=fake_services()))

    response = client.post(
        "/api/v1/chat",
        json={"message": "", "machine_id": "invalid"},
        headers={"X-Correlation-ID": "operator-request-42"},
    )

    assert response.status_code == 422
    assert response.headers["X-Correlation-ID"] == "operator-request-42"
    assert response.json()["error"]["code"] == "request_validation_failed"
    assert response.json()["error"]["request_id"] == "operator-request-42"


def test_unknown_machine_and_session_return_stable_not_found_errors() -> None:
    client = TestClient(create_app(services=fake_services()))

    machine = client.get("/api/v1/machines/P-999/status")
    session = client.get("/api/v1/sessions/SESSION-UNKNOWN")

    assert machine.status_code == 404
    assert machine.json()["error"]["code"] == "machine_not_found"
    assert session.status_code == 404
    assert session.json()["error"]["code"] == "session_not_found"


def test_unconfigured_application_fails_closed() -> None:
    client = TestClient(create_app(), raise_server_exceptions=False)

    response = client.get("/api/v1/machines/P-104/status")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "dependency_unavailable"


def test_readiness_reports_dependency_failure_without_failing_liveness() -> None:
    client = TestClient(create_app(services=fake_services(ready=False)))

    health = client.get("/health")
    readiness = client.get("/ready")

    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    assert readiness.status_code == 503
    assert readiness.json()["status"] == "not_ready"
    assert readiness.json()["dependencies"][0]["status"] == "unavailable"
