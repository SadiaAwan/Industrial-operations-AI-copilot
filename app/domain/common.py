"""Shared domain primitives and validation rules."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

MACHINE_ID_PATTERN = re.compile(r"^[A-Z][A-Z0-9]*-[0-9]{3,6}$")

MachineId = Annotated[str, Field(pattern=MACHINE_ID_PATTERN.pattern)]
Confidence = Annotated[float, Field(ge=0.0, le=1.0)]


class DomainModel(BaseModel):
    """Strict, immutable base for values shared across application layers."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class Severity(StrEnum):
    NORMAL = "normal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MachineStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    DECOMMISSIONED = "decommissioned"


class WorkOrderStatus(StrEnum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class SessionStatus(StrEnum):
    ACTIVE = "active"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    COMPLETED = "completed"
    FAILED = "failed"


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class FeedbackRating(StrEnum):
    HELPFUL = "helpful"
    NOT_HELPFUL = "not_helpful"


def require_utc(value: datetime) -> datetime:
    """Reject naive/non-UTC timestamps and normalize the UTC representation."""

    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError("timestamp must include the UTC timezone")
    return value.astimezone(UTC)
