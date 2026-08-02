"""Bounded session memory for continuing a troubleshooting workflow."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Protocol

from pydantic import Field, field_validator

from app.agent.state import AgentState
from app.domain.common import DomainModel, MachineId, require_utc
from app.domain.work_order import WorkOrderDraft
from app.schemas.tools import (
    DocumentSearchOutput,
    IncidentOutput,
    MaintenanceRecordOutput,
    SensorReadingOutput,
)


class SessionSnapshot(DomainModel):
    session_id: str = Field(min_length=1)
    machine_id: MachineId | None = None
    sensor_data: tuple[SensorReadingOutput, ...] = ()
    documents: tuple[DocumentSearchOutput, ...] = ()
    incidents: tuple[IncidentOutput, ...] = ()
    maintenance: tuple[MaintenanceRecordOutput, ...] = ()
    proposed_action: WorkOrderDraft | None = None
    updated_at: datetime

    @field_validator("updated_at")
    @classmethod
    def timestamp_is_utc(cls, value: datetime) -> datetime:
        return require_utc(value)


class SessionMemory(Protocol):
    async def load(self, session_id: str) -> SessionSnapshot | None: ...

    async def save(self, snapshot: SessionSnapshot) -> None: ...


class InMemorySessionMemory:
    """Process-local adapter for tests; production can implement the protocol."""

    def __init__(self, *, max_sessions: int = 1_000) -> None:
        if max_sessions < 1:
            raise ValueError("max_sessions must be positive")
        self._max_sessions = max_sessions
        self._snapshots: dict[str, SessionSnapshot] = {}
        self._lock = asyncio.Lock()

    async def load(self, session_id: str) -> SessionSnapshot | None:
        if not session_id.strip():
            raise ValueError("session_id must not be empty")
        async with self._lock:
            return self._snapshots.get(session_id)

    async def save(self, snapshot: SessionSnapshot) -> None:
        async with self._lock:
            is_new = snapshot.session_id not in self._snapshots
            if is_new and len(self._snapshots) >= self._max_sessions:
                oldest = min(
                    self._snapshots.values(),
                    key=lambda item: item.updated_at,
                )
                self._snapshots.pop(oldest.session_id)
            self._snapshots[snapshot.session_id] = snapshot


def capture_session(
    state: AgentState,
    *,
    updated_at: datetime,
) -> SessionSnapshot:
    """Capture reusable evidence without storing hidden reasoning."""

    return SessionSnapshot(
        session_id=state["session_id"],
        machine_id=state["machine_id"],
        sensor_data=state["sensor_data"],
        documents=state["documents"],
        incidents=state["incidents"],
        maintenance=state["maintenance"],
        proposed_action=state["proposed_action"],
        updated_at=updated_at,
    )


def restore_session(
    state: AgentState,
    snapshot: SessionSnapshot | None,
) -> AgentState:
    """Restore only the bounded evidence fields for the same session."""

    if snapshot is None:
        return state
    if snapshot.session_id != state["session_id"]:
        raise ValueError("snapshot belongs to another session")
    restored = state.copy()
    restored["machine_id"] = state["machine_id"] or snapshot.machine_id
    restored["sensor_data"] = snapshot.sensor_data
    restored["documents"] = snapshot.documents
    restored["incidents"] = snapshot.incidents
    restored["maintenance"] = snapshot.maintenance
    restored["proposed_action"] = snapshot.proposed_action
    return restored
