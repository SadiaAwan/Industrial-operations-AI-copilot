"""Synchronous and streaming chat endpoints."""

import asyncio
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import StreamingResponse

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


@router.post("/stream", response_class=StreamingResponse)
async def stream_chat_response(
    payload: ChatRequest,
    request: Request,
    services: Annotated[CoreServices, Depends(get_core_services)],
) -> StreamingResponse:
    events = services.chat.stream(payload, request_id=request.state.request_id)

    async def encode_events() -> AsyncIterator[str]:
        try:
            async for event in events:
                if await request.is_disconnected():
                    break
                yield f"event: {event.event}\ndata: {event.model_dump_json()}\n\n"
        except asyncio.CancelledError:
            raise
        finally:
            await events.aclose()

    return StreamingResponse(
        encode_events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
