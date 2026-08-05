"""Privacy controls for user-supplied feedback text."""

from __future__ import annotations

import re

_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE = re.compile(r"(?<!\w)(?:\+?\d[\d ()-]{6,}\d)(?!\w)")
_BEARER = re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE)
_SECRET_ASSIGNMENT = re.compile(
    r"\b(password|secret|token|api[_-]?key)\s*[:=]\s*\S+", re.IGNORECASE
)
MAX_FEEDBACK_COMMENT_LENGTH = 500


def sanitize_feedback_comment(value: str | None) -> str | None:
    """Remove common personal/secret values and bound retained free text."""

    if value is None:
        return None
    sanitized = _EMAIL.sub("[REDACTED_EMAIL]", value)
    sanitized = _PHONE.sub("[REDACTED_PHONE]", sanitized)
    sanitized = _BEARER.sub("Bearer [REDACTED]", sanitized)
    sanitized = _SECRET_ASSIGNMENT.sub(r"\1=[REDACTED]", sanitized)
    sanitized = " ".join(sanitized.split())[:MAX_FEEDBACK_COMMENT_LENGTH]
    return sanitized or None
