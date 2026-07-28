"""Agent session domain contract."""

from datetime import datetime

from pydantic import Field, field_validator

from app.domain.common import DomainModel, MachineId, SessionStatus, require_utc


class AgentSession(DomainModel):
    session_id: str = Field(min_length=1)
    machine_id: MachineId | None = None
    status: SessionStatus = SessionStatus.ACTIVE
    created_at: datetime
    updated_at: datetime
    pending_action_ids: tuple[str, ...] = ()

    @field_validator("created_at", "updated_at")
    @classmethod
    def timestamps_are_utc(cls, value: datetime) -> datetime:
        return require_utc(value)
