"""Typed, bounded HTTP client used by the Streamlit application."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Any, TypeVar
from uuid import uuid4

import httpx
from pydantic import BaseModel, ValidationError

from app.schemas.actions import ApprovalActionResponse, ApprovalDecisionRequest
from app.schemas.api import (
    APIErrorResponse,
    MachineListResponse,
    MachineStatusResponse,
    ReadinessResponse,
)
from app.schemas.chat import ChatRequest, ChatResponse, ChatStreamEvent
from app.schemas.feedback import FeedbackCreate, FeedbackResponse


class CopilotAPIError(RuntimeError):
    """A safe, user-displayable API failure."""

    def __init__(self, code: str, message: str, *, request_id: str | None = None):
        super().__init__(message)
        self.code = code
        self.request_id = request_id


ModelT = TypeVar("ModelT", bound=BaseModel)


@dataclass(frozen=True, slots=True)
class APIClientConfig:
    base_url: str = "http://localhost:8000"
    timeout_seconds: float = 20.0

    def __post_init__(self) -> None:
        if not self.base_url.startswith(("http://", "https://")):
            raise ValueError("base_url must use HTTP or HTTPS")
        if not 0 < self.timeout_seconds <= 120:
            raise ValueError("timeout_seconds must be between 0 and 120")


class CopilotAPIClient:
    def __init__(
        self,
        config: APIClientConfig | None = None,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.config = config or APIClientConfig()
        self._client = httpx.Client(
            base_url=self.config.base_url,
            timeout=self.config.timeout_seconds,
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def get_machine_status(self, machine_id: str) -> MachineStatusResponse:
        response = self._request("GET", f"/api/v1/machines/{machine_id}/status")
        return self._validate(MachineStatusResponse, response.json())

    def list_machines(self) -> MachineListResponse:
        response = self._request("GET", "/api/v1/machines")
        return self._validate(MachineListResponse, response.json())

    def chat(self, payload: ChatRequest) -> ChatResponse:
        response = self._request(
            "POST", "/api/v1/chat", json=payload.model_dump(mode="json")
        )
        return self._validate(ChatResponse, response.json())

    def stream_chat(self, payload: ChatRequest) -> Iterator[ChatStreamEvent]:
        request_id = str(uuid4())
        try:
            with self._client.stream(
                "POST",
                "/api/v1/chat/stream",
                json=payload.model_dump(mode="json"),
                headers={"X-Correlation-ID": request_id},
            ) as response:
                self._raise_for_status(response)
                event_type: str | None = None
                for line in response.iter_lines():
                    if line.startswith("event: "):
                        event_type = line.removeprefix("event: ")
                    elif line.startswith("data: "):
                        event = ChatStreamEvent.model_validate_json(
                            line.removeprefix("data: ")
                        )
                        if event_type is not None and event.event != event_type:
                            raise CopilotAPIError(
                                "invalid_stream",
                                "The event stream contained inconsistent metadata.",
                                request_id=request_id,
                            )
                        yield event
                        event_type = None
        except httpx.TimeoutException as exception:
            raise CopilotAPIError(
                "request_timeout", "The copilot API timed out.", request_id=request_id
            ) from exception
        except httpx.RequestError as exception:
            raise CopilotAPIError(
                "api_unavailable",
                "The copilot API is unavailable.",
                request_id=request_id,
            ) from exception

    def decide_action(
        self,
        action_id: str,
        decision: ApprovalDecisionRequest,
        *,
        approve: bool,
    ) -> ApprovalActionResponse:
        operation = "approve" if approve else "reject"
        response = self._request(
            "POST",
            f"/api/v1/actions/{action_id}/{operation}",
            json=decision.model_dump(mode="json"),
        )
        return self._validate(ApprovalActionResponse, response.json())

    def submit_feedback(self, payload: FeedbackCreate) -> FeedbackResponse:
        response = self._request(
            "POST", "/api/v1/feedback", json=payload.model_dump(mode="json")
        )
        return self._validate(FeedbackResponse, response.json())

    def readiness(self) -> ReadinessResponse:
        response = self._request("GET", "/ready", accepted_statuses={200, 503})
        return self._validate(ReadinessResponse, response.json())

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: Mapping[str, Any] | None = None,
        accepted_statuses: set[int] | None = None,
    ) -> httpx.Response:
        request_id = str(uuid4())
        try:
            response = self._client.request(
                method,
                path,
                json=json,
                headers={"X-Correlation-ID": request_id},
            )
        except httpx.TimeoutException as exception:
            raise CopilotAPIError(
                "request_timeout", "The copilot API timed out.", request_id=request_id
            ) from exception
        except httpx.RequestError as exception:
            raise CopilotAPIError(
                "api_unavailable",
                "The copilot API is unavailable.",
                request_id=request_id,
            ) from exception
        if accepted_statuses is None or response.status_code not in accepted_statuses:
            self._raise_for_status(response)
        return response

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        if not response.is_error:
            return
        try:
            error = APIErrorResponse.model_validate(response.json()).error
        except (ValueError, ValidationError):
            raise CopilotAPIError(
                "api_error", "The copilot API returned an unexpected error."
            ) from None
        raise CopilotAPIError(error.code, error.message, request_id=error.request_id)

    @staticmethod
    def _validate(model: type[ModelT], payload: object) -> ModelT:
        try:
            return model.model_validate(payload)
        except ValidationError as exception:
            raise CopilotAPIError(
                "invalid_response", "The copilot API returned an invalid response."
            ) from exception
