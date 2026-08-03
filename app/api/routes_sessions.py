"""Agent-session query endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import CoreServices, get_core_services
from app.domain.session import AgentSession

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


@router.get("/{session_id}", response_model=AgentSession)
async def get_session(
    session_id: str,
    services: Annotated[CoreServices, Depends(get_core_services)],
) -> AgentSession:
    result = await services.sessions.get(session_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "session_not_found", "message": "Session not found"},
        )
    return result
