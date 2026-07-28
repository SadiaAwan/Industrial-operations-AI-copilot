"""Work-order contracts keep proposals distinct from executed work."""

from datetime import datetime

from pydantic import Field, field_validator

from app.domain.common import (
    DomainModel,
    MachineId,
    Severity,
    WorkOrderStatus,
    require_utc,
)


class WorkOrderDraft(DomainModel):
    draft_id: str = Field(min_length=1)
    machine_id: MachineId
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    priority: Severity
    proposed_checks: tuple[str, ...] = ()
    status: WorkOrderStatus = WorkOrderStatus.PENDING_APPROVAL

    @field_validator("status")
    @classmethod
    def draft_cannot_be_executed(cls, value: WorkOrderStatus) -> WorkOrderStatus:
        if value not in {
            WorkOrderStatus.DRAFT,
            WorkOrderStatus.PENDING_APPROVAL,
            WorkOrderStatus.REJECTED,
        }:
            raise ValueError("a draft cannot represent approved or executed work")
        return value


class WorkOrder(DomainModel):
    work_order_id: str = Field(min_length=1)
    machine_id: MachineId
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    priority: Severity
    status: WorkOrderStatus
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def timestamp_is_utc(cls, value: datetime) -> datetime:
        return require_utc(value)
