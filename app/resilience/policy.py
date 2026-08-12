"""Bounded timeout, retry, and exponential-backoff policy."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Limits dependency calls by time, attempts, and backoff duration."""

    timeout_seconds: float = 5.0
    max_attempts: int = 2
    initial_backoff_seconds: float = 0.05
    backoff_multiplier: float = 2.0
    max_backoff_seconds: float = 1.0

    def __post_init__(self) -> None:
        if not 0 < self.timeout_seconds <= 60:
            raise ValueError("timeout_seconds must be between 0 and 60")
        if not 1 <= self.max_attempts <= 5:
            raise ValueError("max_attempts must be between 1 and 5")
        if self.initial_backoff_seconds < 0:
            raise ValueError("initial_backoff_seconds cannot be negative")
        if self.backoff_multiplier < 1:
            raise ValueError("backoff_multiplier must be at least 1")
        if not 0 <= self.max_backoff_seconds <= 30:
            raise ValueError("max_backoff_seconds must be between 0 and 30")

    def backoff_for(self, completed_attempts: int) -> float:
        """Return the capped delay after a failed attempt."""

        if completed_attempts < 1:
            raise ValueError("completed_attempts must be positive")
        delay = self.initial_backoff_seconds * (
            self.backoff_multiplier ** (completed_attempts - 1)
        )
        return min(delay, self.max_backoff_seconds)


async def run_with_retry[T](
    operation: Callable[[], Awaitable[T]],
    *,
    policy: RetryPolicy,
    is_retryable: Callable[[BaseException], bool],
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> tuple[T, int]:
    """Run an async operation with a finite retry and per-attempt timeout."""

    for attempt in range(1, policy.max_attempts + 1):
        try:
            result = await asyncio.wait_for(operation(), timeout=policy.timeout_seconds)
            return result, attempt
        except BaseException as error:
            if (
                isinstance(error, asyncio.CancelledError)
                or attempt == policy.max_attempts
                or not is_retryable(error)
            ):
                raise
            await sleep(policy.backoff_for(attempt))

    raise AssertionError("bounded retry loop exhausted without a result")
