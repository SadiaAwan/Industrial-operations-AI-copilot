"""Synchronous chat endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.api.dependencies import CoreServices, get_core_services
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


@router.post("", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def create_chat_response(
    payload: ChatRequest,
    request: Request,
    services: Annotated[CoreServices, Depends(get_core_services)],
) -> ChatResponse:
    return await services.chat.chat(payload, request_id=request.state.request_id)
