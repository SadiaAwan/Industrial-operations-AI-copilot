from fastapi.testclient import TestClient

from app.api.mock_services import build_mock_services
from app.config import Settings
from app.main import create_app


def test_mock_runtime_supports_local_ui_without_cloud_calls() -> None:
    services = build_mock_services(Settings(runtime_mode="mock"))

    with TestClient(create_app(services=services)) as client:
        machine = client.get("/api/v1/machines/P-104/status")
        response = client.post(
            "/api/v1/chat",
            json={"message": "Check the pump", "machine_id": "P-104"},
        )

    assert machine.status_code == 200
    assert machine.json()["machine"]["machine_id"] == "P-104"
    assert response.status_code == 200
    assert response.json()["result"]["current_condition"].startswith("Local mock mode")
    assert response.json()["result"]["citations"] == []
