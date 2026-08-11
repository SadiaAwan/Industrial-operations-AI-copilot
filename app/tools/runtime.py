"""Bounded execution policy shared by all agent-facing tools."""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from time import perf_counter

from app.observability.tracing import NullToolTracer, ToolTrace, ToolTracer
from app.resilience.circuit_breaker import CircuitBreaker, CircuitOpenError
from app.resilience.policy import RetryPolicy
from app.schemas.tools import ToolError, ToolErrorCode, ToolResult


class RetryableToolError(RuntimeError):
    """A temporary dependency error that may be retried."""


class ToolNotFoundError(LookupError):
    """The requested domain object does not exist."""


@dataclass(frozen=True, slots=True)
class ToolPolicy:
    timeout_seconds: float = 5.0
    max_attempts: int = 2
    initial_backoff_seconds: float = 0.05
    backoff_multiplier: float = 2.0
    max_backoff_seconds: float = 1.0

    def __post_init__(self) -> None:
        RetryPolicy(
            timeout_seconds=self.timeout_seconds,
            max_attempts=self.max_attempts,
            initial_backoff_seconds=self.initial_backoff_seconds,
            backoff_multiplier=self.backoff_multiplier,
            max_backoff_seconds=self.max_backoff_seconds,
        )

    def backoff_for(self, completed_attempts: int) -> float:
        return RetryPolicy(
            timeout_seconds=self.timeout_seconds,
            max_attempts=self.max_attempts,
            initial_backoff_seconds=self.initial_backoff_seconds,
            backoff_multiplier=self.backoff_multiplier,
            max_backoff_seconds=self.max_backoff_seconds,
        ).backoff_for(completed_attempts)


class ToolExecutor:
    def __init__(
        self,
        *,
        policy: ToolPolicy | None = None,
        tracer: ToolTracer | None = None,
        circuit_breaker: CircuitBreaker | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self.policy = policy or ToolPolicy()
        self.tracer = tracer or NullToolTracer()
        self.circuit_breaker = circuit_breaker
        self._sleep = sleep

    async def execute[T](
        self,
        tool_name: str,
        operation: Callable[[], Awaitable[T]],
    ) -> ToolResult[T]:
        started = perf_counter()
        attempts = 0
        error: ToolError | None = None
        if self.circuit_breaker is not None:
            try:
                self.circuit_breaker.before_call()
            except CircuitOpenError:
                error = ToolError(
                    code=ToolErrorCode.DEPENDENCY_UNAVAILABLE,
                    message=f"{tool_name} dependency is temporarily unavailable",
                    retryable=True,
                )
                self._trace(tool_name, "failed", attempts, started, error.code.value)
                return ToolResult[T](error=error)

        for attempts in range(1, self.policy.max_attempts + 1):
            try:
                data = await asyncio.wait_for(
                    operation(), timeout=self.policy.timeout_seconds
                )
                result = ToolResult[T](data=data)
                if self.circuit_breaker is not None:
                    self.circuit_breaker.record_success()
                self._trace(tool_name, "succeeded", attempts, started)
                return result
            except TimeoutError:
                error = ToolError(
                    code=ToolErrorCode.TIMEOUT,
                    message=f"{tool_name} timed out",
                    retryable=True,
                )
            except RetryableToolError:
                error = ToolError(
                    code=ToolErrorCode.DEPENDENCY_UNAVAILABLE,
                    message=f"{tool_name} dependency is temporarily unavailable",
                    retryable=True,
                )
            except ToolNotFoundError as exception:
                error = ToolError(
                    code=ToolErrorCode.NOT_FOUND,
                    message=str(exception),
                    retryable=False,
                )
                break
            except Exception:
                error = ToolError(
                    code=ToolErrorCode.INTERNAL_ERROR,
                    message=f"{tool_name} failed safely",
                    retryable=False,
                )
                break
            if attempts < self.policy.max_attempts:
                await self._sleep(self.policy.backoff_for(attempts))

        assert error is not None
        if self.circuit_breaker is not None:
            self.circuit_breaker.record_failure()
        self._trace(tool_name, "failed", attempts, started, error.code.value)
        return ToolResult[T](error=error)

    def _trace(
        self,
        tool_name: str,
        status: str,
        attempts: int,
        started: float,
        error_code: str | None = None,
    ) -> None:
        try:
            self.tracer.record(
                ToolTrace(
                    tool_name=tool_name,
                    status=status,
                    attempt_count=attempts,
                    duration_ms=(perf_counter() - started) * 1_000,
                    error_code=error_code,
                )
            )
        except Exception:
            # Observability is optional and must never break the protected operation.
            pass
