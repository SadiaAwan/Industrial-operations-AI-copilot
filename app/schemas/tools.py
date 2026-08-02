"""Validated contracts at the tool boundary."""

from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import Field, field_validator, model_validator

from app.domain.common import DomainModel, MachineId, Severity, require_utc
from app.retrieval.citations import Citation


class LimitedQuery(DomainModel):
    limit: Annotated[int, Field(ge=1, le=100)] = 10


class MachineQuery(LimitedQuery):
    machine_id: MachineId


class SensorDataQuery(MachineQuery):
    start_at: datetime
    end_at: datetime

    @field_validator("start_at", "end_at")
    @classmethod
    def timestamps_are_utc(cls, value: datetime) -> datetime:
        return require_utc(value)

    @model_validator(mode="after")
    def chronological_range(self) -> "SensorDataQuery":
        if self.end_at < self.start_at:
            raise ValueError("end_at must not be earlier than start_at")
        return self


class DocumentSearchQuery(LimitedQuery):
    query: str = Field(min_length=1)
    machine_type: str = Field(min_length=1)


class IncidentSearchQuery(MachineQuery):
    query: str | None = Field(default=None, min_length=1, max_length=500)


class SensorReadingOutput(DomainModel):
    reading_id: str
    machine_id: MachineId
    sensor_type: str
    value: float
    unit: str
    recorded_at: datetime


class IncidentOutput(DomainModel):
    incident_id: str
    machine_id: MachineId
    occurred_at: datetime
    severity: Severity
    summary: str
    root_cause: str | None = None
    resolution: str | None = None


class MaintenanceRecordOutput(DomainModel):
    record_id: str
    machine_id: MachineId
    performed_at: datetime
    maintenance_type: str
    description: str
    technician_id: str | None = None


class DocumentSearchOutput(DomainModel):
    content: str = Field(min_length=1, max_length=5_000)
    score: float = Field(ge=0)
    citation: Citation


class WorkOrderDraftRequest(DomainModel):
    machine_id: MachineId
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=5_000)
    priority: Severity
    proposed_checks: tuple[str, ...] = Field(default=(), max_length=50)


class ToolErrorCode(StrEnum):
    INVALID_INPUT = "invalid_input"
    NOT_FOUND = "not_found"
    TIMEOUT = "timeout"
    DEPENDENCY_UNAVAILABLE = "dependency_unavailable"
    INTERNAL_ERROR = "internal_error"


class ToolError(DomainModel):
    code: ToolErrorCode
    message: str = Field(min_length=1)
    retryable: bool = False


class ToolResult[T](DomainModel):
    data: T | None = None
    error: ToolError | None = None

    @model_validator(mode="after")
    def exactly_one_outcome(self) -> "ToolResult[T]":
        if (self.data is None) == (self.error is None):
            raise ValueError("tool result must contain exactly one of data or error")
        return self
