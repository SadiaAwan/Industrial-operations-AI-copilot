"""Fail-open, privacy-preserving tracing contracts and MLflow adapter."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass, field
from typing import Any, Protocol

SafeAttribute = str | int | float | bool


@dataclass(frozen=True, slots=True)
class SpanRecord:
    """A sanitized span representation used by deterministic tests and adapters."""

    name: str
    span_type: str
    attributes: Mapping[str, SafeAttribute] = field(default_factory=dict)
    status: str = "ok"


class Span(Protocol):
    def set_attribute(self, key: str, value: SafeAttribute) -> None: ...


class Tracer(Protocol):
    def start_span(
        self,
        name: str,
        *,
        span_type: str,
        attributes: Mapping[str, SafeAttribute] | None = None,
    ) -> AbstractContextManager[Span]: ...


class _NullSpan:
    def set_attribute(self, key: str, value: SafeAttribute) -> None:
        del key, value


class NullTracer:
    @contextmanager
    def start_span(
        self,
        name: str,
        *,
        span_type: str,
        attributes: Mapping[str, SafeAttribute] | None = None,
    ) -> Iterator[Span]:
        del name, span_type, attributes
        yield _NullSpan()


class _MemorySpan:
    def __init__(self, attributes: Mapping[str, SafeAttribute] | None) -> None:
        self.attributes = dict(attributes or {})

    def set_attribute(self, key: str, value: SafeAttribute) -> None:
        self.attributes[key] = value


class InMemoryTracer:
    """Records spans without a backend, useful for contract and integration tests."""

    def __init__(self) -> None:
        self.spans: list[SpanRecord] = []

    @contextmanager
    def start_span(
        self,
        name: str,
        *,
        span_type: str,
        attributes: Mapping[str, SafeAttribute] | None = None,
    ) -> Iterator[Span]:
        span = _MemorySpan(attributes)
        status = "ok"
        try:
            yield span
        except Exception:
            status = "error"
            raise
        finally:
            self.spans.append(SpanRecord(name, span_type, span.attributes, status))


class _MlflowSpan:
    def __init__(self, span: Any) -> None:
        self._span = span

    def set_attribute(self, key: str, value: SafeAttribute) -> None:
        try:
            self._span.set_attribute(key, value)
        except Exception:
            pass


class MlflowTracer:
    """MLflow tracing adapter that degrades to no-op if observability fails."""

    @contextmanager
    def start_span(
        self,
        name: str,
        *,
        span_type: str,
        attributes: Mapping[str, SafeAttribute] | None = None,
    ) -> Iterator[Span]:
        try:
            import mlflow  # type: ignore[import-not-found]

            manager = mlflow.start_span(
                name=name,
                span_type=span_type,
                attributes=dict(attributes or {}),
            )
            backend_span = manager.__enter__()
        except Exception:
            # Telemetry must never prevent the protected business operation.
            yield _NullSpan()
            return

        try:
            yield _MlflowSpan(backend_span)
        except BaseException as error:
            try:
                manager.__exit__(type(error), error, error.__traceback__)
            except Exception:
                pass
            raise
        else:
            try:
                manager.__exit__(None, None, None)
            except Exception:
                pass


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


class SpanToolTracer:
    """Bridge bounded tool execution events into privacy-safe tracing spans."""

    def __init__(self, tracer: Tracer) -> None:
        self._tracer = tracer

    def record(self, trace: ToolTrace) -> None:
        attributes: dict[str, SafeAttribute] = {
            "tool.name": trace.tool_name,
            "tool.status": trace.status,
            "tool.attempt_count": trace.attempt_count,
            "tool.duration_ms": trace.duration_ms,
        }
        if trace.error_code is not None:
            attributes["tool.error_code"] = trace.error_code
        try:
            with self._tracer.start_span(
                f"tool.{trace.tool_name}",
                span_type="TOOL",
                attributes=attributes,
            ):
                pass
        except Exception:
            pass
