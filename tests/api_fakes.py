"""Deterministic service doubles shared by phase 8 API tests."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta

from app.api.dependencies import CoreServices
from app.domain.approval import ApprovalAction, canonical_payload_hash
from app.domain.common import (
    ApprovalStatus,
    MachineStatus,
    SessionStatus,
    Severity,
)
from app.domain.feedback import AgentFeedback
from app.domain.machine import Machine
from app.domain.session import AgentSession
from app.schemas.actions import ApprovalActionResponse, ApprovalDecisionRequest
from app.schemas.api import DependencyStatus, MachineStatusResponse
from app.schemas.chat import ChatRequest, ChatResponse, ChatStreamEvent
from app.schemas.feedback import FeedbackCreate, FeedbackResponse
from app.schemas.recommendations import AgentRecommendation

NOW = datetime(2026, 8, 3, 12, 0, tzinfo=UTC)


class FakeChatService:
    def __init__(self) -> None:
        self.stream_closed = False
        self.raise_timeout = False

    async def chat(self, request: ChatRequest, *, request_id: str) -> ChatResponse:
        if self.raise_timeout:
            raise TimeoutError
        session_id = request.session_id or "SESSION-NEW"
        return ChatResponse(
            request_id=request_id,
            session_id=session_id,
            result=AgentRecommendation(
                machine_id=request.machine_id or "P-104",
                current_condition="Stable",
                severity=Severity.NORMAL,
                confidence=0.9,
                observations=(),
                possible_causes=(),
                recommended_checks=(),
                safety_notice="Follow approved safety procedures.",
            ),
        )

    async def stream(
        self, request: ChatRequest, *, request_id: str
    ) -> AsyncGenerator[ChatStreamEvent, None]:
        session_id = request.session_id or "SESSION-NEW"
        try:
            yield ChatStreamEvent(
                event="started",
                request_id=request_id,
                session_id=session_id,
            )
            yield ChatStreamEvent(
                event="completed",
                request_id=request_id,
                session_id=session_id,
                data={"condition": "Stable"},
            )
        finally:
            self.stream_closed = True


class FakeMachineService:
    async def status(self, machine_id: str) -> MachineStatusResponse | None:
        if machine_id != "P-104":
            return None
        return MachineStatusResponse(
            machine=Machine(
                machine_id="P-104",
                name="Cooling Water Pump",
                machine_type="centrifugal_pump",
                status=MachineStatus.ACTIVE,
            )
        )


class FakeSessionService:
    async def get(self, session_id: str) -> AgentSession | None:
        if session_id != "SESSION-1":
            return None
        return AgentSession(
            session_id=session_id,
            machine_id="P-104",
            status=SessionStatus.ACTIVE,
            created_at=NOW,
            updated_at=NOW,
        )


class FakeApprovalService:
    async def decide(
        self,
        action_id: str,
        decision: ApprovalDecisionRequest,
        *,
        approve: bool,
    ) -> ApprovalActionResponse:
        payload = {"machine_id": "P-104"}
        action = ApprovalAction(
            action_id=action_id,
            session_id="SESSION-1",
            requested_by="agent:SESSION-1",
            action_type="create_work_order",
            payload=payload,
            payload_hash=canonical_payload_hash(payload),
            status=ApprovalStatus.APPROVED if approve else ApprovalStatus.REJECTED,
            created_at=NOW,
            expires_at=NOW + timedelta(minutes=15),
            decided_at=NOW + timedelta(minutes=1),
            decided_by=decision.user_id,
        )
        return ApprovalActionResponse(action=action, status=action.status)


class FakeFeedbackService:
    async def create(self, feedback: FeedbackCreate) -> FeedbackResponse:
        return FeedbackResponse(
            feedback=AgentFeedback(
                feedback_id="FEEDBACK-1",
                session_id=feedback.session_id,
                request_id=feedback.request_id,
                trace_id=f"trace-{feedback.request_id}",
                rating=feedback.rating,
                comment=feedback.comment,
                agent_version="phase-08",
                prompt_version="diagnostics-v1",
                prompt_sha256=(
                    "e45959a50682bc17822873a90070a9dcb08208b935415f4aa1ad1aed0e26abeb"
                ),
                model_version="deterministic-v1",
                created_at=NOW,
            )
        )


class FakeReadinessService:
    def __init__(self, *, available: bool = True) -> None:
        self.available = available

    async def check(self) -> tuple[DependencyStatus, ...]:
        return (
            DependencyStatus(
                name="database", status="ready" if self.available else "unavailable"
            ),
        )


def fake_services(*, ready: bool = True) -> CoreServices:
    return CoreServices(
        chat=FakeChatService(),
        machines=FakeMachineService(),
        sessions=FakeSessionService(),
        approvals=FakeApprovalService(),
        feedback=FakeFeedbackService(),
        readiness=FakeReadinessService(available=ready),
    )


__all__ = ["FakeChatService", "fake_services"]
