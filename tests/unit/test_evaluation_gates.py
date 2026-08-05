"""Release gate tests with zero tolerance for critical failures."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.evaluation import (
    EvaluationReport,
    compare_reports,
    load_evaluation_dataset,
    run_evaluation,
)
from app.evaluation.gates import (
    ReleaseGateError,
    enforce_release_gate,
    summarize_release_gate,
)

DATASET = Path("evaluation/expected_outputs/phase11_reference_results.json")
NOW = datetime(2026, 8, 5, 8, 0, tzinfo=UTC)


def report() -> EvaluationReport:
    dataset, fingerprint = load_evaluation_dataset(DATASET)
    return run_evaluation(dataset, fingerprint, generated_at=NOW)


def test_reference_report_passes_release_gate() -> None:
    summary = enforce_release_gate(report())

    assert summary.passed
    assert summary.failures == ()


def test_failed_critical_metric_blocks_release() -> None:
    candidate = report()
    first_case = candidate.cases[0]
    citation = next(
        score for score in first_case.scores if score.metric == "citation_correctness"
    )
    failed_citation = citation.model_copy(update={"value": 0.5, "passed": False})
    failed_case = first_case.model_copy(
        update={
            "scores": tuple(
                failed_citation if score is citation else score
                for score in first_case.scores
            ),
            "passed": False,
        }
    )
    candidate = candidate.model_copy(
        update={"cases": (failed_case, *candidate.cases[1:]), "passed": False}
    )

    with pytest.raises(ReleaseGateError) as caught:
        enforce_release_gate(candidate)

    assert caught.value.summary.failures[0].critical
    assert caught.value.summary.failures[0].metric == "citation_correctness"


def test_regression_blocks_otherwise_passing_candidate() -> None:
    baseline = report()
    candidate = baseline.model_copy(
        update={"metric_averages": {**baseline.metric_averages, "latency": 0.9}}
    )
    comparison = compare_reports(baseline, candidate)

    summary = summarize_release_gate(candidate, comparison)

    assert not summary.passed
    assert summary.regression_metrics == ("latency",)
