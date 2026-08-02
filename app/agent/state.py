"""Typed state shared by every node in the operations-agent graph."""

from __future__ import annotations

import operator
from datetime import datetime
from enum import StrEnum
from typing import Annotated, NotRequired, TypedDict

from app.domain.work_order import WorkOrderDraft
from app.schemas.recommendations import AgentRecommendation, ToolCallSummary
from app.schemas.tools import (
    DocumentSearchOutput,
    IncidentOutput,
    MaintenanceRecordOutput,
    SensorReadingOutput,
    ToolError,
)


class AgentIntent(StrEnum):
    DIAGNOSTIC = "diagnostic"
    SENSOR_STATUS = "sensor_status"
    INCIDENT_SEARCH = "incident_search"
    MAINTENANCE_HISTORY = "maintenance_history"
    SAFETY_PROCEDURE = "safety_procedure"
    WORK_ORDER_DRAFT = "work_order_draft"


class AgentOutcome(StrEnum):
    COMPLETED = "completed"
    CLARIFICATION_REQUIRED = "clarification_required"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    MACHINE_NOT_FOUND = "machine_not_found"
    TOOL_FAILURE = "tool_failure"
    LOOP_LIMIT_REACHED = "loop_limit_reached"


class AgentState(TypedDict):
    """Serializable graph state; append-only fields use explicit reducers."""

    message: str
    session_id: str
    machine_id: str | None
    intent: NotRequired[AgentIntent]
    started_at: datetime
    sensor_window_hours: int
    max_steps: int
    step_count: int
    clarification_required: bool
    evidence_sufficient: bool
    sensor_data: tuple[SensorReadingOutput, ...]
    documents: tuple[DocumentSearchOutput, ...]
    incidents: tuple[IncidentOutput, ...]
    maintenance: tuple[MaintenanceRecordOutput, ...]
    proposed_action: WorkOrderDraft | None
    recommendation: AgentRecommendation | None
    outcome: AgentOutcome | None
    errors: Annotated[tuple[ToolError, ...], operator.add]
    tool_calls: Annotated[tuple[ToolCallSummary, ...], operator.add]


def initial_agent_state(
    *,
    message: str,
    session_id: str,
    machine_id: str | None,
    started_at: datetime,
    sensor_window_hours: int = 4,
    max_steps: int = 20,
) -> AgentState:
    """Create state with bounded operational defaults."""

    if not message.strip():
        raise ValueError("message must not be empty")
    if not session_id.strip():
        raise ValueError("session_id must not be empty")
    if sensor_window_hours < 1 or sensor_window_hours > 24:
        raise ValueError("sensor_window_hours must be between 1 and 24")
    if max_steps < 1 or max_steps > 50:
        raise ValueError("max_steps must be between 1 and 50")
    if started_at.tzinfo is None or started_at.utcoffset() is None:
        raise ValueError("started_at must be timezone-aware")

    return AgentState(
        message=message.strip(),
        session_id=session_id.strip(),
        machine_id=machine_id,
        started_at=started_at,
        sensor_window_hours=sensor_window_hours,
        max_steps=max_steps,
        step_count=0,
        clarification_required=False,
        evidence_sufficient=False,
        sensor_data=(),
        documents=(),
        incidents=(),
        maintenance=(),
        proposed_action=None,
        recommendation=None,
        outcome=None,
        errors=(),
        tool_calls=(),
    )
