"""Bounded primary/fallback execution with explicit degradation metadata."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass


class ServiceUnavailableError(RuntimeError):
    """Safe public error used when primary and fallback are both unavailable."""


@dataclass(frozen=True, slots=True)
class FallbackResult[T]:
    value: T
    degraded: bool = False
    source: str = "primary"


async def call_with_fallback[T](
    primary: Callable[[], Awaitable[T]],
    fallback: Callable[[], Awaitable[T]],
    *,
    timeout_seconds: float = 5.0,
    fallback_timeout_seconds: float = 2.0,
    on_degraded: Callable[[], None] | None = None,
) -> FallbackResult[T]:
    """Use a separately bounded fallback without exposing dependency details."""

    if timeout_seconds <= 0 or fallback_timeout_seconds <= 0:
        raise ValueError("fallback timeouts must be positive")

    try:
        value = await asyncio.wait_for(primary(), timeout=timeout_seconds)
        return FallbackResult(value=value)
    except asyncio.CancelledError:
        raise
    except Exception:
        if on_degraded is not None:
            try:
                on_degraded()
            except Exception:
                pass

    try:
        value = await asyncio.wait_for(
            fallback(), timeout=fallback_timeout_seconds
        )
        return FallbackResult(value=value, degraded=True, source="fallback")
    except asyncio.CancelledError:
        raise
    except Exception as error:
        raise ServiceUnavailableError(
            "service is temporarily unavailable; retry later"
        ) from error
