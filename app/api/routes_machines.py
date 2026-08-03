"""Machine status endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import CoreServices, get_core_services
from app.schemas.api import MachineStatusResponse

router = APIRouter(prefix="/api/v1/machines", tags=["machines"])


@router.get("/{machine_id}/status", response_model=MachineStatusResponse)
async def get_machine_status(
    machine_id: str,
    services: Annotated[CoreServices, Depends(get_core_services)],
) -> MachineStatusResponse:
    result = await services.machines.status(machine_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "machine_not_found", "message": "Machine not found"},
        )
    return result
