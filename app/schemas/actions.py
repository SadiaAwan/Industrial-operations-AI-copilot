"""Approval API contracts."""

from pydantic import Field

from app.domain.approval import ApprovalAction
from app.domain.common import ApprovalStatus, DomainModel


class ApprovalDecisionRequest(DomainModel):
    user_id: str = Field(min_length=1)
    payload_hash: str = Field(min_length=1)


class ApprovalActionResponse(DomainModel):
    action: ApprovalAction
    status: ApprovalStatus
