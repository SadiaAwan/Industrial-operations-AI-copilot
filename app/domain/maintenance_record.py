"""Maintenance history domain contract."""

from datetime import datetime

from pydantic import Field, field_validator

from app.domain.common import DomainModel, MachineId, require_utc


class MaintenanceRecord(DomainModel):
    record_id: str = Field(min_length=1)
    machine_id: MachineId
    performed_at: datetime
    maintenance_type: str = Field(min_length=1)
    description: str = Field(min_length=1)
    technician_id: str | None = None

    @field_validator("performed_at")
    @classmethod
    def timestamp_is_utc(cls, value: datetime) -> datetime:
        return require_utc(value)
