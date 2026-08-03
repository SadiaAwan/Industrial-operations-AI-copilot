"""FastAPI application factory for the Industrial Operations Copilot."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError

from app.api.dependencies import CoreServices
from app.api.errors import (
    approval_error_handler,
    http_error_handler,
    timeout_error_handler,
    unavailable_error_handler,
    validation_error_handler,
)
from app.api.routes_actions import router as actions_router
from app.api.routes_chat import router as chat_router
from app.api.routes_feedback import router as feedback_router
from app.api.routes_health import router as health_router
from app.api.routes_machines import router as machines_router
from app.api.routes_sessions import router as sessions_router
from app.approval.workflow import ApprovalWorkflowError

RequestHandler = Callable[[Request], Awaitable[Response]]


def create_app(*, services: CoreServices | None = None) -> FastAPI:
    application = FastAPI(
        title="Industrial AI Operations Copilot API",
        version="1.0.0",
        description="Grounded decision support; no autonomous equipment control.",
    )
    if services is not None:
        application.state.core_services = services

    @application.middleware("http")
    async def correlation_id_middleware(
        request: Request, call_next: RequestHandler
    ) -> Response:
        supplied_id = request.headers.get("X-Correlation-ID", "").strip()
        request_id = supplied_id[:128] if supplied_id else str(uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = request_id
        return response

    application.add_exception_handler(
        RequestValidationError,
        validation_error_handler,  # type: ignore[arg-type]
    )
    application.add_exception_handler(
        HTTPException,
        http_error_handler,  # type: ignore[arg-type]
    )
    application.add_exception_handler(
        ApprovalWorkflowError,
        approval_error_handler,
    )
    application.add_exception_handler(
        TimeoutError,
        timeout_error_handler,  # type: ignore[arg-type]
    )
    application.add_exception_handler(
        RuntimeError,
        unavailable_error_handler,  # type: ignore[arg-type]
    )

    application.include_router(chat_router)
    application.include_router(machines_router)
    application.include_router(sessions_router)
    application.include_router(actions_router)
    application.include_router(feedback_router)
    application.include_router(health_router)
    return application


app = create_app()
