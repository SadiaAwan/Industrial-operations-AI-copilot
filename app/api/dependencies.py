"""Explicit application-service dependencies used by the HTTP layer."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Protocol, cast

from fastapi import Request

from app.domain.session import AgentSession
from app.schemas.api import MachineStatusResponse
from app.schemas.chat import ChatRequest, ChatResponse, ChatStreamEvent


class ChatAPI(Protocol):
    async def chat(self, request: ChatRequest, *, request_id: str) -> ChatResponse: ...

    def stream(
        self, request: ChatRequest, *, request_id: str
    ) -> AsyncIterator[ChatStreamEvent]: ...


class MachineAPI(Protocol):
    async def status(self, machine_id: str) -> MachineStatusResponse | None: ...


class SessionAPI(Protocol):
    async def get(self, session_id: str) -> AgentSession | None: ...


@dataclass(frozen=True, slots=True)
class CoreServices:
    chat: ChatAPI
    machines: MachineAPI
    sessions: SessionAPI


def get_core_services(request: Request) -> CoreServices:
    """Resolve app-scoped services without creating hidden global state."""

    services = getattr(request.app.state, "core_services", None)
    if services is None:
        raise RuntimeError("core API services are not configured")
    return cast(CoreServices, services)
