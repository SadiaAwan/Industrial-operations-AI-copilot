"""Explicit application-service dependencies used by the HTTP layer."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol, cast

from fastapi import Request

from app.domain.session import AgentSession
from app.schemas.actions import ApprovalActionResponse, ApprovalDecisionRequest
from app.schemas.api import MachineStatusResponse
from app.schemas.chat import ChatRequest, ChatResponse, ChatStreamEvent
from app.schemas.feedback import FeedbackCreate, FeedbackResponse


class ChatAPI(Protocol):
    async def chat(self, request: ChatRequest, *, request_id: str) -> ChatResponse: ...

    def stream(
        self, request: ChatRequest, *, request_id: str
    ) -> AsyncIterator[ChatStreamEvent]: ...


class MachineAPI(Protocol):
    async def status(self, machine_id: str) -> MachineStatusResponse | None: ...


class SessionAPI(Protocol):
    async def get(self, session_id: str) -> AgentSession | None: ...


class ApprovalAPI(Protocol):
    async def decide(
        self,
        action_id: str,
        decision: ApprovalDecisionRequest,
        *,
        approve: bool,
    ) -> ApprovalActionResponse: ...


class FeedbackAPI(Protocol):
    async def create(self, feedback: FeedbackCreate) -> FeedbackResponse: ...


@dataclass(frozen=True, slots=True)
class CoreServices:
    chat: ChatAPI
    machines: MachineAPI
    sessions: SessionAPI
    approvals: ApprovalAPI
    feedback: FeedbackAPI


def get_core_services(request: Request) -> CoreServices:
    """Resolve app-scoped services without creating hidden global state."""

    services = getattr(request.app.state, "core_services", None)
    if services is None:
        raise RuntimeError("core API services are not configured")
    return cast(CoreServices, services)
