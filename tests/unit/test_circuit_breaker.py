"""Deterministic circuit-breaker state transition tests."""

import pytest

from app.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerPolicy,
    CircuitOpenError,
    CircuitState,
)


def test_circuit_opens_at_threshold_and_blocks_calls() -> None:
    breaker = CircuitBreaker(CircuitBreakerPolicy(failure_threshold=2))

    breaker.record_failure()
    assert breaker.state.value == CircuitState.CLOSED.value
    breaker.record_failure()

    assert breaker.state.value == CircuitState.OPEN.value
    with pytest.raises(CircuitOpenError):
        breaker.before_call()


def test_half_open_probe_recovers_after_success() -> None:
    now = 10.0
    breaker = CircuitBreaker(
        CircuitBreakerPolicy(failure_threshold=1, recovery_timeout_seconds=5),
        clock=lambda: now,
    )
    breaker.record_failure()

    now = 15.0
    assert breaker.state.value == CircuitState.HALF_OPEN.value
    breaker.before_call()
    breaker.record_success()

    assert breaker.state.value == CircuitState.CLOSED.value


def test_failed_half_open_probe_reopens_circuit() -> None:
    now = 10.0
    breaker = CircuitBreaker(
        CircuitBreakerPolicy(failure_threshold=1, recovery_timeout_seconds=5),
        clock=lambda: now,
    )
    breaker.record_failure()

    now = 15.0
    breaker.before_call()
    breaker.record_failure()

    assert breaker.state.value == CircuitState.OPEN.value
