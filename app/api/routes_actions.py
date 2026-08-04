"""Human approval and rejection endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import CoreServices, get_core_services
from app.schemas.actions import ApprovalActionResponse, ApprovalDecisionRequest

router = APIRouter(prefix="/api/v1/actions", tags=["approvals"])


@router.post("/{action_id}/approve", response_model=ApprovalActionResponse)
async def approve_action(
    action_id: str,
    payload: ApprovalDecisionRequest,
    services: Annotated[CoreServices, Depends(get_core_services)],
) -> ApprovalActionResponse:
    return await services.approvals.decide(action_id, payload, approve=True)


@router.post("/{action_id}/reject", response_model=ApprovalActionResponse)
async def reject_action(
    action_id: str,
    payload: ApprovalDecisionRequest,
    services: Annotated[CoreServices, Depends(get_core_services)],
) -> ApprovalActionResponse:
    return await services.approvals.decide(action_id, payload, approve=False)
