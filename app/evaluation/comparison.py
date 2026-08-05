"""Baseline comparison that blocks material metric regressions."""

from __future__ import annotations

from app.evaluation.models import EvaluationModel, EvaluationReport


class MetricRegression(EvaluationModel):
    metric: str
    baseline: float
    candidate: float
    delta: float


class EvaluationComparison(EvaluationModel):
    regressions: tuple[MetricRegression, ...]
    passed: bool


def compare_reports(
    baseline: EvaluationReport,
    candidate: EvaluationReport,
    *,
    tolerance: float = 0.0,
) -> EvaluationComparison:
    if not 0 <= tolerance <= 1:
        raise ValueError("tolerance must be between 0 and 1")
    common_metrics = baseline.metric_averages.keys() & candidate.metric_averages.keys()
    regressions = tuple(
        MetricRegression(
            metric=metric,
            baseline=baseline.metric_averages[metric],
            candidate=candidate.metric_averages[metric],
            delta=candidate.metric_averages[metric] - baseline.metric_averages[metric],
        )
        for metric in sorted(common_metrics)
        if candidate.metric_averages[metric]
        < baseline.metric_averages[metric] - tolerance
    )
    return EvaluationComparison(regressions=regressions, passed=not regressions)
