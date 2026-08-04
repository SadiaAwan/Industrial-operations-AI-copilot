"""Bounded in-process metrics registry with Prometheus exposition."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from threading import Lock

from app.observability.tracing import ToolTrace

LabelSet = tuple[tuple[str, str], ...]
DEFAULT_LATENCY_BUCKETS = (0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)


def _labels(labels: Mapping[str, str] | None) -> LabelSet:
    return tuple(sorted((key, value[:128]) for key, value in (labels or {}).items()))


def _label_text(labels: LabelSet, extra: tuple[str, str] | None = None) -> str:
    values = (*labels, *((extra,) if extra else ()))
    if not values:
        return ""
    escaped = []
    for key, value in values:
        safe_value = value.replace("\\", "\\\\").replace('"', '\\"')
        escaped.append(f'{key}="{safe_value}"')
    return "{" + ",".join(escaped) + "}"


@dataclass(slots=True)
class _Histogram:
    buckets: tuple[float, ...]
    counts: list[int]
    count: int = 0
    total: float = 0.0

    def observe(self, value: float) -> None:
        self.count += 1
        self.total += value
        for index, upper_bound in enumerate(self.buckets):
            if value <= upper_bound:
                self.counts[index] += 1


class MetricRegistry:
    """Thread-safe registry intentionally limited to declared application metrics."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._counters: dict[tuple[str, LabelSet], float] = defaultdict(float)
        self._histograms: dict[tuple[str, LabelSet], _Histogram] = {}

    def increment(
        self,
        name: str,
        *,
        value: float = 1,
        labels: Mapping[str, str] | None = None,
    ) -> None:
        if value < 0:
            raise ValueError("counter increments must be non-negative")
        with self._lock:
            self._counters[(name, _labels(labels))] += value

    def observe(
        self,
        name: str,
        value: float,
        *,
        labels: Mapping[str, str] | None = None,
        buckets: Sequence[float] = DEFAULT_LATENCY_BUCKETS,
    ) -> None:
        normalized_buckets = tuple(sorted(set(buckets)))
        key = (name, _labels(labels))
        with self._lock:
            histogram = self._histograms.get(key)
            if histogram is None:
                histogram = _Histogram(
                    normalized_buckets, [0 for _ in normalized_buckets]
                )
                self._histograms[key] = histogram
            elif histogram.buckets != normalized_buckets:
                raise ValueError("histogram buckets cannot change")
            histogram.observe(value)

    def render_prometheus(self) -> str:
        lines: list[str] = []
        with self._lock:
            for (name, labels), value in sorted(self._counters.items()):
                lines.append(f"{name}{_label_text(labels)} {value:g}")
            for (name, labels), histogram in sorted(self._histograms.items()):
                for upper_bound, count in zip(
                    histogram.buckets, histogram.counts, strict=True
                ):
                    bucket_labels = _label_text(labels, ("le", f"{upper_bound:g}"))
                    lines.append(
                        f"{name}_bucket{bucket_labels} {count}"
                    )
                infinite_labels = _label_text(labels, ("le", "+Inf"))
                lines.append(
                    f"{name}_bucket{infinite_labels} {histogram.count}"
                )
                lines.append(f"{name}_sum{_label_text(labels)} {histogram.total:g}")
                lines.append(f"{name}_count{_label_text(labels)} {histogram.count}")
        return "\n".join(lines) + ("\n" if lines else "")


class ObservabilityMetrics:
    """Low-cardinality metric operations used by API, agent, and tool layers."""

    def __init__(self, registry: MetricRegistry | None = None) -> None:
        self.registry = registry or MetricRegistry()

    def record_request(self, *, method: str, status_code: int, duration: float) -> None:
        labels = {"method": method, "status_class": f"{status_code // 100}xx"}
        self.registry.increment("copilot_http_requests_total", labels=labels)
        self.registry.observe(
            "copilot_http_request_duration_seconds", duration, labels=labels
        )

    def record_tool(
        self, *, tool_name: str, status: str, duration: float, attempts: int
    ) -> None:
        labels = {"tool": tool_name, "status": status}
        self.registry.increment("copilot_tool_calls_total", labels=labels)
        self.registry.observe("copilot_tool_duration_seconds", duration, labels=labels)
        if attempts > 1:
            self.registry.increment(
                "copilot_tool_retries_total",
                value=attempts - 1,
                labels={"tool": tool_name},
            )

    def record_tokens(
        self, *, model: str, input_tokens: int, output_tokens: int
    ) -> None:
        self.registry.increment(
            "copilot_tokens_total",
            value=input_tokens,
            labels={"model": model, "direction": "input"},
        )
        self.registry.increment(
            "copilot_tokens_total",
            value=output_tokens,
            labels={"model": model, "direction": "output"},
        )


class MetricsToolTracer:
    """ToolTracer adapter for status, latency, timeout, and retry metrics."""

    def __init__(self, metrics: ObservabilityMetrics) -> None:
        self._metrics = metrics

    def record(self, trace: ToolTrace) -> None:
        try:
            self._metrics.record_tool(
                tool_name=trace.tool_name,
                status=trace.status,
                duration=trace.duration_ms / 1_000,
                attempts=trace.attempt_count,
            )
            if trace.error_code == "timeout":
                self._metrics.registry.increment(
                    "copilot_tool_timeouts_total", labels={"tool": trace.tool_name}
                )
        except Exception:
            pass
