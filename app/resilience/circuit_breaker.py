"""Small in-process circuit breaker for repeatedly failing dependencies."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from time import monotonic


class CircuitState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(RuntimeError):
    """Raised when a protected dependency is temporarily short-circuited."""


@dataclass(frozen=True, slots=True)
class CircuitBreakerPolicy:
    failure_threshold: int = 3
    recovery_timeout_seconds: float = 30.0

    def __post_init__(self) -> None:
        if not 1 <= self.failure_threshold <= 20:
            raise ValueError("failure_threshold must be between 1 and 20")
        if not 0 < self.recovery_timeout_seconds <= 3_600:
            raise ValueError("recovery_timeout_seconds must be between 0 and 3600")


class CircuitBreaker:
    """Tracks failures and permits one probe after the recovery timeout."""

    def __init__(
        self,
        policy: CircuitBreakerPolicy | None = None,
        *,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self.policy = policy or CircuitBreakerPolicy()
        self._clock = clock
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._opened_at: float | None = None

    @property
    def state(self) -> CircuitState:
        if self._state is CircuitState.OPEN and self._recovery_elapsed():
            return CircuitState.HALF_OPEN
        return self._state

    def before_call(self) -> None:
        current_state = self.state
        if current_state is CircuitState.OPEN:
            raise CircuitOpenError("dependency circuit is open")
        if current_state is CircuitState.HALF_OPEN:
            self._state = CircuitState.HALF_OPEN

    def record_success(self) -> None:
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._opened_at = None

    def record_failure(self) -> None:
        if self.state is CircuitState.HALF_OPEN:
            self._open()
            return
        self._failure_count += 1
        if self._failure_count >= self.policy.failure_threshold:
            self._open()

    def _open(self) -> None:
        self._state = CircuitState.OPEN
        self._opened_at = self._clock()

    def _recovery_elapsed(self) -> bool:
        return self._opened_at is not None and (
            self._clock() - self._opened_at
            >= self.policy.recovery_timeout_seconds
        )
