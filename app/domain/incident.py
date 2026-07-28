"""Incident domain contract."""

from datetime import datetime

from pydantic import Field, field_validator

from app.domain.common import DomainModel, MachineId, Severity, require_utc


class Incident(DomainModel):
    incident_id: str = Field(min_length=1)
    machine_id: MachineId
    occurred_at: datetime
    severity: Severity
    summary: str = Field(min_length=1)
    root_cause: str | None = None
    resolution: str | None = None

    @field_validator("occurred_at")
    @classmethod
    def timestamp_is_utc(cls, value: datetime) -> datetime:
        return require_utc(value)
