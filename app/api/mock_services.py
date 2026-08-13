"""Deterministic, cloud-free services for the local container environment."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.agent.model import DeterministicRecommendationGenerator, RecommendationContext
from app.agent.routing import classify_intent
from app.api.dependencies import CoreServices
from app.config import Settings
from app.database.models import MachineModel
from app.database.repositories import (
    IncidentRepository,
    MachineRepository,
    MaintenanceRepository,
    SensorReadingRepository,
)
from app.database.session import create_database_engine, create_session_factory
from app.domain.common import MachineStatus, SessionStatus, Severity
from app.domain.feedback import AgentFeedback
from app.domain.machine import Machine
from app.domain.session import AgentSession
from app.schemas.actions import ApprovalActionResponse, ApprovalDecisionRequest
from app.schemas.api import DependencyStatus, MachineStatusResponse
from app.schemas.chat import ChatRequest, ChatResponse, ChatStreamEvent
from app.schemas.feedback import FeedbackCreate, FeedbackResponse
from app.schemas.recommendations import AgentRecommendation, RecommendedCheck
from app.schemas.tools import (
    IncidentOutput,
    MaintenanceRecordOutput,
    SensorReadingOutput,
)

PROMPT_SHA256 = "e45959a50682bc17822873a90070a9dcb08208b935415f4aa1ad1aed0e26abeb"
MACHINES = {
    "P-101": Machine(
        machine_id="P-101",
        name="Cooling Water Pump 1",
        machine_type="centrifugal_pump",
        status=MachineStatus.ACTIVE,
        location="Utilities / Cooling loop A",
    ),
    "P-102": Machine(
        machine_id="P-102",
        name="Process Feed Pump 2",
        machine_type="centrifugal_pump",
        status=MachineStatus.ACTIVE,
        location="Process Area / Feed train",
    ),
    "P-103": Machine(
        machine_id="P-103",
        name="Transfer Pump 3",
        machine_type="centrifugal_pump",
        status=MachineStatus.MAINTENANCE,
        location="Tank Farm / Transfer line",
    ),
    "P-104": Machine(
        machine_id="P-104",
        name="Cooling Water Pump 4",
        machine_type="centrifugal_pump",
        status=MachineStatus.ACTIVE,
        location="Utilities / Cooling loop B",
    ),
    "P-105": Machine(
        machine_id="P-105",
        name="Booster Pump 5",
        machine_type="centrifugal_pump",
        status=MachineStatus.ACTIVE,
        location="Distribution / Booster station",
    ),
}


class MockRuntime:
    """Implements the API protocols without external model or search calls."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._sessions: dict[str, AgentSession] = {}
        self._engine = create_database_engine(settings)
        self._session_factory = create_session_factory(self._engine)
        self._generator = DeterministicRecommendationGenerator()

    @staticmethod
    def _machine(row: MachineModel) -> Machine:
        return Machine.model_validate(
            {
                "machine_id": row.machine_id,
                "name": row.name,
                "machine_type": row.machine_type,
                "status": row.status,
                "location": row.location,
            }
        )

    def _evidence(
        self, machine_id: str
    ) -> tuple[
        tuple[SensorReadingOutput, ...],
        tuple[IncidentOutput, ...],
        tuple[MaintenanceRecordOutput, ...],
    ]:
        with self._session_factory() as session:
            readings = SensorReadingRepository(session).for_machine(
                machine_id, limit=100
            )
            incidents = IncidentRepository(session).search(machine_id, limit=5)
            maintenance = MaintenanceRepository(session).for_machine(
                machine_id, limit=5
            )
            return (
                tuple(
                    SensorReadingOutput(
                        reading_id=row.reading_id,
                        machine_id=row.machine_id,
                        sensor_type=row.sensor_type,
                        value=row.value,
                        unit=row.unit,
                        recorded_at=row.recorded_at,
                    )
                    for row in readings
                ),
                tuple(
                    IncidentOutput(
                        incident_id=row.incident_id,
                        machine_id=row.machine_id,
                        occurred_at=row.occurred_at,
                        severity=row.severity,
                        summary=row.summary,
                        root_cause=row.root_cause,
                        resolution=row.resolution,
                    )
                    for row in incidents
                ),
                tuple(
                    MaintenanceRecordOutput(
                        record_id=row.record_id,
                        machine_id=row.machine_id,
                        performed_at=row.performed_at,
                        maintenance_type=row.maintenance_type,
                        description=row.description,
                        technician_id=row.technician_id,
                    )
                    for row in maintenance
                ),
            )

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
        try:
            sensor_data, incidents, maintenance = self._evidence(machine_id)
            recommendation = await self._generator.generate(
                RecommendationContext(
                    machine_id=machine_id,
                    message=request.message,
                    intent=classify_intent(request.message),
                    sensor_data=sensor_data,
                    incidents=incidents,
                    maintenance=maintenance,
                )
            )
        except SQLAlchemyError:
            recommendation = AgentRecommendation(
                machine_id=machine_id,
                current_condition="Local mock mode: database evidence is unavailable.",
                severity=Severity.NORMAL,
                confidence=0.0,
                observations=(),
                possible_causes=(),
                recommended_checks=(
                    RecommendedCheck(
                        instruction="Restore the local database connection.",
                        rationale="A grounded diagnosis requires machine evidence.",
                    ),
                ),
                safety_notice="Advisory only. Follow approved safety procedures.",
            )
        return ChatResponse(
            request_id=request_id,
            session_id=session_id,
            result=recommendation,
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

    async def list(self) -> tuple[Machine, ...]:
        try:
            with self._session_factory() as session:
                rows = MachineRepository(session).list(limit=100)
                return tuple(self._machine(row) for row in rows)
        except SQLAlchemyError:
            return tuple(MACHINES.values())

    async def status(self, machine_id: str) -> MachineStatusResponse | None:
        try:
            with self._session_factory() as session:
                row = MachineRepository(session).get(machine_id)
                if row is None:
                    return None
                readings = SensorReadingRepository(session).for_machine(
                    machine_id, limit=100
                )
                return MachineStatusResponse(
                    machine=self._machine(row),
                    latest_readings=tuple(
                        SensorReadingOutput(
                            reading_id=item.reading_id,
                            machine_id=item.machine_id,
                            sensor_type=item.sensor_type,
                            value=item.value,
                            unit=item.unit,
                            recorded_at=item.recorded_at,
                        )
                        for item in readings
                    ),
                )
        except SQLAlchemyError:
            machine = MACHINES.get(machine_id)
            return (
                MachineStatusResponse(machine=machine)
                if machine is not None
                else None
            )

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
