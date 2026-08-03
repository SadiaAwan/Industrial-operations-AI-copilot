"""End-to-end HTTP workflow tests over injected application services."""

import asyncio
from collections.abc import AsyncGenerator
from typing import cast

from fastapi.testclient import TestClient
from starlette.requests import Request

from app.api.dependencies import CoreServices
from app.api.routes_chat import stream_chat_response
from app.main import create_app
from app.schemas.chat import ChatRequest
from tests.api_fakes import FakeChatService, fake_services


def test_chat_and_streaming_workflows_preserve_request_identity() -> None:
    services = fake_services()
    client = TestClient(create_app(services=services))
    payload = {"message": "Show current status", "machine_id": "P-104"}

    response = client.post(
        "/api/v1/chat", json=payload, headers={"X-Correlation-ID": "REQ-8"}
    )
    stream = client.post(
        "/api/v1/chat/stream",
        json=payload,
        headers={"X-Correlation-ID": "STREAM-8"},
    )

    assert response.status_code == 200
    assert response.json()["request_id"] == "REQ-8"
    assert response.json()["result"]["machine_id"] == "P-104"
    assert stream.status_code == 200
    assert stream.headers["content-type"].startswith("text/event-stream")
    assert "event: started" in stream.text
    assert "event: completed" in stream.text
    assert '"request_id":"STREAM-8"' in stream.text
    assert isinstance(services.chat, FakeChatService)
    assert services.chat.stream_closed


def test_timeout_is_mapped_without_leaking_an_internal_exception() -> None:
    services = fake_services()
    assert isinstance(services.chat, FakeChatService)
    services.chat.raise_timeout = True
    client = TestClient(create_app(services=services), raise_server_exceptions=False)

    response = client.post("/api/v1/chat", json={"message": "Status P-104"})

    assert response.status_code == 504
    assert response.json()["error"]["code"] == "request_timeout"


def test_approval_rejection_and_feedback_are_exposed_as_separate_actions() -> None:
    client = TestClient(create_app(services=fake_services()))
    decision = {"user_id": "operator-1", "payload_hash": "approved-payload-hash"}

    approved = client.post("/api/v1/actions/ACT-1/approve", json=decision)
    rejected = client.post("/api/v1/actions/ACT-2/reject", json=decision)
    feedback = client.post(
        "/api/v1/feedback",
        json={
            "session_id": "SESSION-1",
            "request_id": "REQ-1",
            "rating": "helpful",
            "comment": "Grounded and clear",
        },
    )

    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    assert feedback.status_code == 201
    assert feedback.json()["feedback"]["rating"] == "helpful"


def test_machine_and_session_success_contracts() -> None:
    services: CoreServices = fake_services()
    client = TestClient(create_app(services=services))

    machine = client.get("/api/v1/machines/P-104/status")
    session = client.get("/api/v1/sessions/SESSION-1")

    assert machine.status_code == 200
    assert machine.json()["machine"]["machine_id"] == "P-104"
    assert session.status_code == 200
    assert session.json()["machine_id"] == "P-104"


def test_aborted_stream_closes_upstream_generator() -> None:
    services = fake_services()
    assert isinstance(services.chat, FakeChatService)
    application = create_app(services=services)

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"", "more_body": False}

    request = Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/api/v1/chat/stream",
            "raw_path": b"/api/v1/chat/stream",
            "query_string": b"",
            "headers": [],
            "client": ("test", 1),
            "server": ("test", 80),
            "app": application,
        },
        receive=receive,
    )
    request.state.request_id = "STREAM-CANCELLED"

    async def consume_one_event_then_cancel() -> None:
        response = await stream_chat_response(
            ChatRequest(message="Status", machine_id="P-104"), request, services
        )
        iterator = cast(AsyncGenerator[str, None], response.body_iterator)
        assert "event: started" in await anext(iterator)
        await iterator.aclose()

    asyncio.run(consume_one_event_then_cancel())

    assert services.chat.stream_closed
