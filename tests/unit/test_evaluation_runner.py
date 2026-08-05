"""Dataset, runner, report, tracking, and comparison tests."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.evaluation import (
    EvaluationDatasetError,
    NullEvaluationTracker,
    compare_reports,
    load_evaluation_dataset,
    render_report,
    run_evaluation,
    write_report,
)

DATASET = Path("evaluation/expected_outputs/phase11_reference_results.json")
NOW = datetime(2026, 8, 5, 8, 0, tzinfo=UTC)


def test_reference_dataset_is_fingerprinted_and_reproducible() -> None:
    first_dataset, first_hash = load_evaluation_dataset(DATASET)
    second_dataset, second_hash = load_evaluation_dataset(DATASET)

    assert first_dataset == second_dataset
    assert first_hash == second_hash
    assert len(first_hash) == 64


def test_reference_suite_passes_every_metric() -> None:
    dataset, fingerprint = load_evaluation_dataset(DATASET)
    report = run_evaluation(dataset, fingerprint, generated_at=NOW)

    assert report.passed
    assert all(value == 1 for value in report.metric_averages.values())
    assert all(case.passed for case in report.cases)


def test_report_is_stable_json_and_written_atomically(tmp_path: Path) -> None:
    dataset, fingerprint = load_evaluation_dataset(DATASET)
    report = run_evaluation(dataset, fingerprint, generated_at=NOW)
    output = tmp_path / "nested" / "report.json"

    write_report(report, output)

    assert output.read_text(encoding="utf-8") == render_report(report)
    assert not output.with_suffix(".json.tmp").exists()


def test_duplicate_case_ids_are_rejected(tmp_path: Path) -> None:
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text(
        '{"dataset_id":"x","dataset_version":"1","results":['
        '{"case_id":"A","expected_outcome":"x","actual_outcome":"x",'
        '"latency_ms":0,"estimated_cost_usd":0},'
        '{"case_id":"A","expected_outcome":"x","actual_outcome":"x",'
        '"latency_ms":0,"estimated_cost_usd":0}]}',
        encoding="utf-8",
    )

    with pytest.raises(EvaluationDatasetError, match="unique"):
        load_evaluation_dataset(duplicate)


def test_comparison_detects_metric_regression() -> None:
    dataset, fingerprint = load_evaluation_dataset(DATASET)
    baseline = run_evaluation(dataset, fingerprint, generated_at=NOW)
    candidate = baseline.model_copy(
        update={"metric_averages": {**baseline.metric_averages, "groundedness": 0.8}}
    )

    comparison = compare_reports(baseline, candidate)

    assert not comparison.passed
    assert comparison.regressions[0].metric == "groundedness"


def test_null_tracker_does_not_modify_report() -> None:
    dataset, fingerprint = load_evaluation_dataset(DATASET)
    report = run_evaluation(dataset, fingerprint, generated_at=NOW)
    original = report.model_copy(deep=True)

    NullEvaluationTracker().record(report)

    assert report == original
