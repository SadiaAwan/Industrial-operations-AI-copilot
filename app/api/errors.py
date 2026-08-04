"""Stable error mapping for public API responses."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.approval.workflow import (
    ApprovalExpired,
    ApprovalNotFound,
    ApprovalPayloadMismatch,
    ApprovalReplayBlocked,
    ApprovalUserMismatch,
)
from app.schemas.api import APIErrorDetail, APIErrorResponse


def error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    payload = APIErrorResponse(
        error=APIErrorDetail(
            code=code,
            message=message,
            request_id=getattr(request.state, "request_id", "unavailable"),
            details=details or {},
        )
    )
    return JSONResponse(
        status_code=status_code, content=payload.model_dump(mode="json")
    )


async def validation_error_handler(
    request: Request, exception: RequestValidationError
) -> JSONResponse:
    return error_response(
        request,
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        code="request_validation_failed",
        message="The request did not satisfy the API contract",
        details={"violations": exception.errors()},
    )


async def http_error_handler(
    request: Request, exception: HTTPException
) -> JSONResponse:
    detail = exception.detail
    if isinstance(detail, dict):
        code = str(detail.get("code", "http_error"))
        message = str(detail.get("message", "Request failed"))
    else:
        code = "http_error"
        message = str(detail)
    return error_response(
        request, status_code=exception.status_code, code=code, message=message
    )


async def approval_error_handler(
    request: Request, exception: Exception
) -> JSONResponse:
    if isinstance(exception, ApprovalNotFound):
        return error_response(
            request,
            status_code=status.HTTP_404_NOT_FOUND,
            code="approval_not_found",
            message=str(exception),
        )
    if isinstance(exception, ApprovalExpired):
        response_status = status.HTTP_410_GONE
        code = "approval_expired"
    elif isinstance(exception, ApprovalUserMismatch):
        response_status = status.HTTP_403_FORBIDDEN
        code = "approval_user_mismatch"
    elif isinstance(exception, ApprovalPayloadMismatch):
        response_status = status.HTTP_409_CONFLICT
        code = "approval_payload_mismatch"
    elif isinstance(exception, ApprovalReplayBlocked):
        response_status = status.HTTP_409_CONFLICT
        code = "approval_replay_blocked"
    else:
        response_status = status.HTTP_500_INTERNAL_SERVER_ERROR
        code = "internal_error"
    return error_response(
        request, status_code=response_status, code=code, message=str(exception)
    )


async def timeout_error_handler(
    request: Request, exception: TimeoutError
) -> JSONResponse:
    return error_response(
        request,
        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
        code="request_timeout",
        message="The operation timed out",
    )


async def unavailable_error_handler(
    request: Request, exception: RuntimeError
) -> JSONResponse:
    return error_response(
        request,
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        code="dependency_unavailable",
        message=str(exception),
    )
