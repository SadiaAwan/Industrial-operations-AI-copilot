"""Minimal provider-neutral tracing contract used by tool calls."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ToolTrace:
    tool_name: str
    status: str
    attempt_count: int
    duration_ms: float
    error_code: str | None = None


class ToolTracer(Protocol):
    def record(self, trace: ToolTrace) -> None: ...


class NullToolTracer:
    def record(self, trace: ToolTrace) -> None:
        del trace


class InMemoryToolTracer:
    def __init__(self) -> None:
        self.traces: list[ToolTrace] = []

    def record(self, trace: ToolTrace) -> None:
        self.traces.append(trace)
