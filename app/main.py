"""FastAPI application factory for the Industrial Operations Copilot."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from time import perf_counter
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
from app.api.routes_metrics import router as metrics_router
from app.api.routes_sessions import router as sessions_router
from app.approval.workflow import ApprovalWorkflowError
from app.config import get_settings
from app.observability.logging import (
    bind_log_context,
    configure_structured_logging,
    reset_log_context,
    safe_log,
)
from app.observability.metrics import ObservabilityMetrics
from app.observability.mlflow_utils import configure_mlflow
from app.observability.tracing import MlflowTracer, Tracer

RequestHandler = Callable[[Request], Awaitable[Response]]


def create_app(
    *,
    services: CoreServices | None = None,
    tracer: Tracer | None = None,
    metrics: ObservabilityMetrics | None = None,
) -> FastAPI:
    application = FastAPI(
        title="Industrial AI Operations Copilot API",
        version="1.0.0",
        description="Grounded decision support; no autonomous equipment control.",
    )
    if services is not None:
        application.state.core_services = services
    application.state.tracer = tracer or MlflowTracer()
    application.state.logger = configure_structured_logging()
    application.state.metrics = metrics or ObservabilityMetrics()

    @application.middleware("http")
    async def correlation_id_middleware(
        request: Request, call_next: RequestHandler
    ) -> Response:
        supplied_id = request.headers.get("X-Correlation-ID", "").strip()
        request_id = supplied_id[:128] if supplied_id else str(uuid4())
        request.state.request_id = request_id
        context_tokens = bind_log_context(correlation_id=request_id)
        started = perf_counter()
        attributes = {
            "http.method": request.method,
            "correlation.id": request_id,
        }
        try:
            with application.state.tracer.start_span(
                "http.request", span_type="CHAIN", attributes=attributes
            ) as span:
                response = await call_next(request)
                span.set_attribute("http.status_code", response.status_code)
                route = getattr(request.scope.get("route"), "path", "unmatched")
                span.set_attribute("http.route", route)
            response.headers["X-Correlation-ID"] = request_id
            safe_log(
                application.state.logger,
                logging.INFO,
                "http_request_completed",
                method=request.method,
                route=route,
                status_code=response.status_code,
                duration_ms=(perf_counter() - started) * 1_000,
            )
            try:
                application.state.metrics.record_request(
                    method=request.method,
                    status_code=response.status_code,
                    duration=perf_counter() - started,
                )
            except Exception:
                pass
            return response
        finally:
            reset_log_context(context_tokens)

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
    application.include_router(metrics_router)
    return application


settings = get_settings()
configure_mlflow(settings)
if settings.runtime_mode == "mock":
    from app.api.mock_services import build_mock_services

    app = create_app(services=build_mock_services(settings))
else:
    app = create_app()
