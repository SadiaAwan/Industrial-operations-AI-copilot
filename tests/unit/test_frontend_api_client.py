"""HTTP boundary tests for the typed Streamlit API client."""

from datetime import UTC, datetime

import httpx
import pytest

from app.domain.common import MachineStatus, Severity
from app.domain.machine import Machine
from app.schemas.api import (
    APIErrorDetail,
    APIErrorResponse,
    MachineStatusResponse,
)
from app.schemas.chat import ChatRequest, ChatResponse, ChatStreamEvent
from app.schemas.recommendations import AgentRecommendation
from frontend.api_client import APIClientConfig, CopilotAPIClient, CopilotAPIError

NOW = datetime(2026, 8, 4, 8, 0, tzinfo=UTC)


def recommendation() -> AgentRecommendation:
    return AgentRecommendation(
        machine_id="P-104",
        current_condition="Stable",
        severity=Severity.NORMAL,
        confidence=0.91,
        observations=(),
        possible_causes=(),
        recommended_checks=(),
        safety_notice="Follow approved procedures.",
    )


def test_status_and_chat_responses_are_validated() -> None:
    status = MachineStatusResponse(
        machine=Machine(
            machine_id="P-104",
            name="Cooling Water Pump",
            machine_type="centrifugal_pump",
            status=MachineStatus.ACTIVE,
        )
    )
    chat = ChatResponse(
        request_id="REQ-1",
        session_id="SESSION-1",
        result=recommendation(),
    )

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/status"):
            return httpx.Response(200, json=status.model_dump(mode="json"))
        return httpx.Response(200, json=chat.model_dump(mode="json"))

    client = CopilotAPIClient(transport=httpx.MockTransport(handler))

    assert client.get_machine_status("P-104") == status
    assert client.chat(ChatRequest(message="Status", machine_id="P-104")) == chat
    client.close()


def test_structured_api_error_is_preserved_for_ui() -> None:
    error = APIErrorResponse(
        error=APIErrorDetail(
            code="machine_not_found",
            message="Machine not found",
            request_id="REQ-404",
        )
    )
    client = CopilotAPIClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                404, json=error.model_dump(mode="json"), request=request
            )
        )
    )

    with pytest.raises(CopilotAPIError) as caught:
        client.get_machine_status("P-999")

    assert caught.value.code == "machine_not_found"
    assert caught.value.request_id == "REQ-404"
    assert str(caught.value) == "Machine not found"
    client.close()


def test_unreachable_api_returns_safe_public_message() -> None:
    def unavailable(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("private infrastructure detail", request=request)

    client = CopilotAPIClient(transport=httpx.MockTransport(unavailable))

    with pytest.raises(CopilotAPIError) as caught:
        client.get_machine_status("P-104")

    assert caught.value.code == "api_unavailable"
    assert "private infrastructure detail" not in str(caught.value)
    client.close()


def test_sse_events_are_parsed_and_metadata_must_match() -> None:
    event = ChatStreamEvent(
        event="completed",
        request_id="REQ-STREAM",
        session_id="SESSION-1",
        data={"condition": "Stable"},
    )
    content = f"event: completed\ndata: {event.model_dump_json()}\n\n"
    client = CopilotAPIClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, text=content, request=request)
        )
    )

    events = list(client.stream_chat(ChatRequest(message="Status", machine_id="P-104")))

    assert events == [event]
    client.close()


@pytest.mark.parametrize(
    ("base_url", "timeout"),
    [("localhost:8000", 20), ("http://localhost:8000", 0)],
)
def test_invalid_client_configuration_is_rejected(
    base_url: str, timeout: float
) -> None:
    with pytest.raises(ValueError):
        APIClientConfig(base_url=base_url, timeout_seconds=timeout)
