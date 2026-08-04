"""Agent feedback endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import CoreServices, get_core_services
from app.schemas.feedback import FeedbackCreate, FeedbackResponse

router = APIRouter(prefix="/api/v1/feedback", tags=["feedback"])


@router.post(
    "", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED
)
async def create_feedback(
    payload: FeedbackCreate,
    services: Annotated[CoreServices, Depends(get_core_services)],
) -> FeedbackResponse:
    return await services.feedback.create(payload)
