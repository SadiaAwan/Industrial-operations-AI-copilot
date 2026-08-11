"""Process liveness and dependency readiness endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.api.dependencies import CoreServices, get_core_services
from app.schemas.api import HealthResponse, ReadinessResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse()


@router.get("/ready", response_model=ReadinessResponse)
async def ready(
    response: Response,
    services: Annotated[CoreServices, Depends(get_core_services)],
) -> ReadinessResponse:
    dependencies = await services.readiness.check()
    is_ready = all(
        item.status != "unavailable" or not item.required
        for item in dependencies
    )
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessResponse(
        status="ready" if is_ready else "not_ready", dependencies=dependencies
    )
