"""Validated contracts at the tool boundary."""

from datetime import datetime
from typing import Annotated

from pydantic import Field, field_validator

from app.domain.common import DomainModel, MachineId, require_utc
from app.domain.work_order import WorkOrderDraft


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


class DocumentSearchQuery(LimitedQuery):
    query: str = Field(min_length=1)
    machine_type: str = Field(min_length=1)


class WorkOrderDraftRequest(DomainModel):
    draft: WorkOrderDraft


class ToolError(DomainModel):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    retryable: bool = False


class ToolResult[T](DomainModel):
    data: T | None = None
    error: ToolError | None = None
