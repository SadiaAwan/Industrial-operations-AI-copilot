"""Human approval domain contract."""

from datetime import datetime
from typing import Any

from pydantic import Field, field_validator, model_validator

from app.domain.common import ApprovalStatus, DomainModel, require_utc


class ApprovalAction(DomainModel):
    action_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    requested_by: str = Field(min_length=1)
    action_type: str = Field(min_length=1)
    payload: dict[str, Any]
    payload_hash: str = Field(min_length=1)
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: datetime
    expires_at: datetime
    decided_at: datetime | None = None
    decided_by: str | None = None

    @field_validator("created_at", "expires_at", "decided_at")
    @classmethod
    def timestamps_are_utc(cls, value: datetime | None) -> datetime | None:
        return require_utc(value) if value is not None else None

    @model_validator(mode="after")
    def validate_decision_state(self) -> "ApprovalAction":
        if self.expires_at <= self.created_at:
            raise ValueError("expires_at must be later than created_at")
        decided = self.status in {ApprovalStatus.APPROVED, ApprovalStatus.REJECTED}
        if decided != (self.decided_at is not None and self.decided_by is not None):
            raise ValueError("approved/rejected actions require decision metadata")
        return self
