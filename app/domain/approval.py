"""Human approval domain contract."""

import hashlib
import json
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from pydantic import Field, field_validator, model_validator

from app.domain.common import ApprovalStatus, DomainModel, require_utc


def canonical_payload_hash(payload: Mapping[str, Any]) -> str:
    """Bind approval to an exact, stable JSON payload."""

    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


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
    executed_at: datetime | None = None

    @field_validator("created_at", "expires_at", "decided_at", "executed_at")
    @classmethod
    def timestamps_are_utc(cls, value: datetime | None) -> datetime | None:
        return require_utc(value) if value is not None else None

    @model_validator(mode="after")
    def validate_decision_state(self) -> "ApprovalAction":
        if self.expires_at <= self.created_at:
            raise ValueError("expires_at must be later than created_at")
        decided = self.status in {
            ApprovalStatus.APPROVED,
            ApprovalStatus.REJECTED,
            ApprovalStatus.EXECUTED,
        }
        if decided != (self.decided_at is not None and self.decided_by is not None):
            raise ValueError("approved/rejected actions require decision metadata")
        executed = self.status == ApprovalStatus.EXECUTED
        if executed != (self.executed_at is not None):
            raise ValueError("only executed actions may contain executed_at")
        if self.payload_hash != canonical_payload_hash(self.payload):
            raise ValueError("payload_hash does not match the exact payload")
        return self
