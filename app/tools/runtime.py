"""Bounded execution policy shared by all agent-facing tools."""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from time import perf_counter

from app.observability.tracing import NullToolTracer, ToolTrace, ToolTracer
from app.schemas.tools import ToolError, ToolErrorCode, ToolResult


class RetryableToolError(RuntimeError):
    """A temporary dependency error that may be retried."""


class ToolNotFoundError(LookupError):
    """The requested domain object does not exist."""


@dataclass(frozen=True, slots=True)
class ToolPolicy:
    timeout_seconds: float = 5.0
    max_attempts: int = 2

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0 or self.timeout_seconds > 60:
            raise ValueError("timeout_seconds must be between 0 and 60")
        if self.max_attempts < 1 or self.max_attempts > 3:
            raise ValueError("max_attempts must be between 1 and 3")


class ToolExecutor:
    def __init__(
        self,
        *,
        policy: ToolPolicy | None = None,
        tracer: ToolTracer | None = None,
    ) -> None:
        self.policy = policy or ToolPolicy()
        self.tracer = tracer or NullToolTracer()

    async def execute[T](
        self,
        tool_name: str,
        operation: Callable[[], Awaitable[T]],
    ) -> ToolResult[T]:
        started = perf_counter()
        attempts = 0
        error: ToolError | None = None
        for attempts in range(1, self.policy.max_attempts + 1):
            try:
                data = await asyncio.wait_for(
                    operation(), timeout=self.policy.timeout_seconds
                )
                result = ToolResult[T](data=data)
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
                await asyncio.sleep(0)

        assert error is not None
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
        self.tracer.record(
            ToolTrace(
                tool_name=tool_name,
                status=status,
                attempt_count=attempts,
                duration_ms=(perf_counter() - started) * 1_000,
                error_code=error_code,
            )
        )
