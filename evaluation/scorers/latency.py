"""Latency service-level objective scorer."""

from evaluation.scorers.contracts import EvaluationResult, MetricScore


def score_latency(
    result: EvaluationResult, *, maximum_ms: float = 10_000
) -> MetricScore:
    if maximum_ms <= 0:
        raise ValueError("maximum_ms must be positive")
    value = min(1.0, maximum_ms / max(result.latency_ms, maximum_ms))
    return MetricScore(
        metric="latency",
        value=value,
        threshold=1.0,
        passed=result.latency_ms <= maximum_ms,
        details={"latency_ms": result.latency_ms, "maximum_ms": maximum_ms},
    )
