"""Structured application logging with correlation context and redaction."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Mapping
from contextvars import ContextVar, Token
from datetime import UTC, datetime
from typing import Any

_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)
_session_id: ContextVar[str | None] = ContextVar("session_id", default=None)
_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "authorization",
        "content",
        "cookie",
        "message",
        "password",
        "prompt",
        "secret",
        "token",
    }
)
_BEARER = re.compile(r"(?i)bearer\s+[a-z0-9._~+/=-]+")
_CONNECTION_SECRET = re.compile(r"(?i)(password|pwd|api[_-]?key)=([^;\s]+)")
_MAX_VALUE_LENGTH = 512


def bind_log_context(
    *, correlation_id: str, session_id: str | None = None
) -> tuple[Token[str | None], Token[str | None]]:
    """Bind request context and return reset tokens for middleware cleanup."""

    return _correlation_id.set(correlation_id), _session_id.set(session_id)


def reset_log_context(tokens: tuple[Token[str | None], Token[str | None]]) -> None:
    _correlation_id.reset(tokens[0])
    _session_id.reset(tokens[1])


def _sensitive_key(key: str) -> bool:
    normalized = key.casefold().replace("-", "_")
    return any(part in _SENSITIVE_KEYS for part in normalized.split("."))


def _sanitize_string(value: str) -> str:
    sanitized = _BEARER.sub("Bearer [REDACTED]", value)
    sanitized = _CONNECTION_SECRET.sub(r"\1=[REDACTED]", sanitized)
    if len(sanitized) > _MAX_VALUE_LENGTH:
        return f"{sanitized[:_MAX_VALUE_LENGTH]}…"
    return sanitized


def redact(value: Any, *, key: str = "") -> Any:
    """Recursively sanitize fields before serialization or backend transport."""

    if key and _sensitive_key(key):
        return "[REDACTED]"
    if isinstance(value, Mapping):
        return {
            str(item_key): redact(item, key=str(item_key))
            for item_key, item in value.items()
        }
    if isinstance(value, (list, tuple, set, frozenset)):
        return [redact(item) for item in value]
    if isinstance(value, str):
        return _sanitize_string(value)
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return _sanitize_string(str(value))


class JsonFormatter(logging.Formatter):
    """Emit one bounded JSON object per event."""

    def format(self, record: logging.LogRecord) -> str:
        event: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": _sanitize_string(record.getMessage()),
        }
        correlation_id = _correlation_id.get()
        session_id = _session_id.get()
        if correlation_id:
            event["correlation_id"] = correlation_id
        if session_id:
            event["session_id"] = session_id
        fields = getattr(record, "structured_fields", None)
        if isinstance(fields, Mapping):
            event.update(redact(fields))
        if record.exc_info:
            exception_type = record.exc_info[0]
            if exception_type is not None:
                event["exception_type"] = exception_type.__name__
        return json.dumps(event, ensure_ascii=False, separators=(",", ":"))


def configure_structured_logging(level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger("industrial_copilot")
    if not any(
        isinstance(handler.formatter, JsonFormatter) for handler in logger.handlers
    ):
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger


def safe_log(
    logger: logging.Logger,
    level: int,
    event: str,
    **fields: Any,
) -> None:
    """Log observability metadata without letting telemetry break a request."""

    try:
        logger.log(level, event, extra={"structured_fields": redact(fields)})
    except Exception:
        pass
