"""Contracts for bounded retries, timeouts, and exponential backoff."""

import asyncio

import pytest

from app.resilience.policy import RetryPolicy, run_with_retry


def test_retry_stops_at_configured_attempt_limit() -> None:
    attempts = 0
    delays: list[float] = []

    async def failing_operation() -> str:
        nonlocal attempts
        attempts += 1
        raise ConnectionError("temporary")

    async def record_sleep(delay: float) -> None:
        delays.append(delay)

    policy = RetryPolicy(
        max_attempts=3,
        initial_backoff_seconds=0.1,
        backoff_multiplier=2,
        max_backoff_seconds=0.15,
    )

    with pytest.raises(ConnectionError, match="temporary"):
        asyncio.run(
            run_with_retry(
                failing_operation,
                policy=policy,
                is_retryable=lambda error: isinstance(error, ConnectionError),
                sleep=record_sleep,
            )
        )

    assert attempts == 3
    assert delays == [0.1, 0.15]


def test_timeout_is_bounded_and_can_be_marked_non_retryable() -> None:
    attempts = 0

    async def slow_operation() -> str:
        nonlocal attempts
        attempts += 1
        await asyncio.sleep(0.05)
        return "late"

    with pytest.raises(TimeoutError):
        asyncio.run(
            run_with_retry(
                slow_operation,
                policy=RetryPolicy(timeout_seconds=0.001, max_attempts=5),
                is_retryable=lambda error: False,
            )
        )

    assert attempts == 1


def test_invalid_or_unbounded_retry_configuration_is_rejected() -> None:
    with pytest.raises(ValueError, match="max_attempts"):
        RetryPolicy(max_attempts=0)
    with pytest.raises(ValueError, match="max_attempts"):
        RetryPolicy(max_attempts=6)
