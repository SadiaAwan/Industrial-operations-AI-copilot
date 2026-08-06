"""Deterministic, cloud-free services for the local container environment."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import text

from app.api.dependencies import CoreServices
from app.config import Settings
from app.database.session import create_database_engine
from app.domain.common import MachineStatus, SessionStatus, Severity
from app.domain.feedback import AgentFeedback
from app.domain.machine import Machine
from app.domain.session import AgentSession
from app.schemas.actions import ApprovalActionResponse, ApprovalDecisionRequest
from app.schemas.api import DependencyStatus, MachineStatusResponse
from app.schemas.chat import ChatRequest, ChatResponse, ChatStreamEvent
from app.schemas.feedback import FeedbackCreate, FeedbackResponse
from app.schemas.recommendations import AgentRecommendation, RecommendedCheck

PROMPT_SHA256 = "e45959a50682bc17822873a90070a9dcb08208b935415f4aa1ad1aed0e26abeb"
MACHINES = {
    "P-104": Machine(
        machine_id="P-104",
        name="Cooling Water Pump",
        machine_type="centrifugal_pump",
        status=MachineStatus.ACTIVE,
    ),
    "P-205": Machine(
        machine_id="P-205",
        name="Process Transfer Pump",
        machine_type="centrifugal_pump",
        status=MachineStatus.ACTIVE,
    ),
    "P-307": Machine(
        machine_id="P-307",
        name="Boiler Feed Pump",
        machine_type="centrifugal_pump",
        status=MachineStatus.MAINTENANCE,
    ),
}


class MockRuntime:
    """Implements the API protocols without external model or search calls."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._sessions: dict[str, AgentSession] = {}

    async def chat(self, request: ChatRequest, *, request_id: str) -> ChatResponse:
        now = datetime.now(UTC)
        session_id = request.session_id or f"local-{uuid4()}"
        machine_id = request.machine_id or "P-104"
        self._sessions[session_id] = AgentSession(
            session_id=session_id,
            machine_id=machine_id,
            status=SessionStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        return ChatResponse(
            request_id=request_id,
            session_id=session_id,
            result=AgentRecommendation(
                machine_id=machine_id,
                current_condition="Local mock mode: no live diagnosis was performed.",
                severity=Severity.NORMAL,
                confidence=1.0,
                observations=(),
                possible_causes=(),
                recommended_checks=(
                    RecommendedCheck(
                        instruction="Connect an approved cloud runtime for diagnosis.",
                        rationale=(
                            "Local mode intentionally performs no paid model calls."
                        ),
                    ),
                ),
                safety_notice="Advisory only. Follow approved safety procedures.",
            ),
        )

    async def stream(
        self, request: ChatRequest, *, request_id: str
    ) -> AsyncGenerator[ChatStreamEvent, None]:
        response = await self.chat(request, request_id=request_id)
        yield ChatStreamEvent(
            event="started", request_id=request_id, session_id=response.session_id
        )
        yield ChatStreamEvent(
            event="completed",
            request_id=request_id,
            session_id=response.session_id,
            data=response.result.model_dump(mode="json"),
        )

    async def status(self, machine_id: str) -> MachineStatusResponse | None:
        machine = MACHINES.get(machine_id)
        return MachineStatusResponse(machine=machine) if machine is not None else None

    async def get(self, session_id: str) -> AgentSession | None:
        return self._sessions.get(session_id)

    async def decide(
        self,
        action_id: str,
        decision: ApprovalDecisionRequest,
        *,
        approve: bool,
    ) -> ApprovalActionResponse:
        del action_id, decision, approve
        raise RuntimeError("mock mode does not create approval actions")

    async def create(self, feedback: FeedbackCreate) -> FeedbackResponse:
        now = datetime.now(UTC)
        return FeedbackResponse(
            feedback=AgentFeedback(
                feedback_id=f"local-{uuid4()}",
                session_id=feedback.session_id,
                request_id=feedback.request_id,
                trace_id=f"local-{feedback.request_id}"[:128],
                rating=feedback.rating,
                comment=feedback.comment,
                agent_version="phase-13-local",
                prompt_version="diagnostics-v1",
                prompt_sha256=PROMPT_SHA256,
                model_version="deterministic-local-v1",
                created_at=now,
            )
        )

    async def check(self) -> tuple[DependencyStatus, ...]:
        engine = create_database_engine(self._settings)
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except Exception:
            database_status = "unavailable"
        else:
            database_status = "ready"
        finally:
            engine.dispose()
        return (
            DependencyStatus(name="database", status=database_status),
            DependencyStatus(name="mock-runtime", status="ready"),
        )


def build_mock_services(settings: Settings) -> CoreServices:
    runtime = MockRuntime(settings)
    return CoreServices(
        chat=runtime,
        machines=runtime,
        sessions=runtime,
        approvals=runtime,
        feedback=runtime,
        readiness=runtime,
    )
