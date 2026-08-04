from __future__ import annotations

import io
import json
import logging
from typing import Any

from app.observability.logging import (
    JsonFormatter,
    bind_log_context,
    redact,
    reset_log_context,
    safe_log,
)


def _capturing_logger(stream: io.StringIO) -> logging.Logger:
    logger = logging.Logger("observability-test")
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    return logger


def test_json_log_contains_correlation_context_and_safe_fields() -> None:
    stream = io.StringIO()
    logger = _capturing_logger(stream)
    tokens = bind_log_context(correlation_id="req-42", session_id="SESSION-7")
    try:
        safe_log(logger, logging.INFO, "tool_completed", tool="sensor", attempts=1)
    finally:
        reset_log_context(tokens)

    event = json.loads(stream.getvalue())
    assert event["event"] == "tool_completed"
    assert event["correlation_id"] == "req-42"
    assert event["session_id"] == "SESSION-7"
    assert event["tool"] == "sensor"


def test_secret_and_sensitive_content_are_recursively_redacted() -> None:
    sanitized = redact(
        {
            "api_key": "super-secret-key",
            "nested": {"password": "hunter2", "machine_id": "P-104"},
            "prompt": "private operator question",
            "header": "Bearer abc.def.ghi",
            "dsn": "host=db;password=db-secret;port=5432",
        }
    )

    serialized = json.dumps(sanitized)
    assert "super-secret-key" not in serialized
    assert "hunter2" not in serialized
    assert "private operator question" not in serialized
    assert "abc.def.ghi" not in serialized
    assert "db-secret" not in serialized
    assert sanitized["nested"]["machine_id"] == "P-104"


def test_safe_log_swallows_logging_backend_failure() -> None:
    class FailingLogger:
        def log(self, *_args: Any, **_kwargs: Any) -> None:
            raise RuntimeError("logging backend unavailable")

    safe_log(FailingLogger(), logging.INFO, "request_completed", status=200)  # type: ignore[arg-type]
