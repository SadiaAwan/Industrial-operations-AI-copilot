"""Release gates for quality, safety, approval, and regressions."""

from __future__ import annotations

from pydantic import Field

from app.evaluation.comparison import EvaluationComparison
from app.evaluation.models import EvaluationModel, EvaluationReport


class ReleaseGateFailure(EvaluationModel):
    case_id: str = Field(min_length=1)
    metric: str = Field(min_length=1)
    value: float
    threshold: float
    critical: bool


class ReleaseGateSummary(EvaluationModel):
    passed: bool
    failures: tuple[ReleaseGateFailure, ...]
    regression_metrics: tuple[str, ...] = ()


class ReleaseGateError(RuntimeError):
    def __init__(self, summary: ReleaseGateSummary) -> None:
        super().__init__(
            f"evaluation release gate failed with {len(summary.failures)} "
            f"quality failures and {len(summary.regression_metrics)} regressions"
        )
        self.summary = summary


def summarize_release_gate(
    report: EvaluationReport,
    comparison: EvaluationComparison | None = None,
) -> ReleaseGateSummary:
    failures = tuple(
        ReleaseGateFailure(
            case_id=case.case_id,
            metric=score.metric,
            value=score.value,
            threshold=score.threshold,
            critical=score.critical,
        )
        for case in report.cases
        for score in case.scores
        if not score.passed
    )
    regressions = (
        tuple(regression.metric for regression in comparison.regressions)
        if comparison is not None
        else ()
    )
    return ReleaseGateSummary(
        passed=report.passed and not failures and not regressions,
        failures=failures,
        regression_metrics=regressions,
    )


def enforce_release_gate(
    report: EvaluationReport,
    comparison: EvaluationComparison | None = None,
) -> ReleaseGateSummary:
    summary = summarize_release_gate(report, comparison)
    if not summary.passed:
        raise ReleaseGateError(summary)
    return summary
