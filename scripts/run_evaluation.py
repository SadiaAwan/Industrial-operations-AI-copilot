"""Run the deterministic evaluation suite and enforce release gates."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from pydantic import ValidationError

from app.evaluation import (
    EvaluationReport,
    EvaluationThresholds,
    MlflowEvaluationTracker,
    NullEvaluationTracker,
    compare_reports,
    load_evaluation_dataset,
    run_evaluation,
    write_report,
)
from app.evaluation.gates import ReleaseGateError, enforce_release_gate

DEFAULT_DATASET = Path("evaluation/expected_outputs/phase11_reference_results.json")
DEFAULT_THRESHOLDS = Path("evaluation/release_thresholds.json")
DEFAULT_REPORT = Path("evaluation/reports/latest.json")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--thresholds", type=Path, default=DEFAULT_THRESHOLDS)
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--baseline-report", type=Path)
    parser.add_argument("--regression-tolerance", type=float, default=0.0)
    parser.add_argument("--track-mlflow", action="store_true")
    return parser


def _load_thresholds(path: Path) -> EvaluationThresholds:
    try:
        return EvaluationThresholds.model_validate_json(path.read_bytes())
    except (OSError, ValidationError) as exception:
        raise ValueError(f"invalid evaluation thresholds: {path}") from exception


def _load_report(path: Path) -> EvaluationReport:
    try:
        return EvaluationReport.model_validate_json(path.read_bytes())
    except (OSError, ValidationError) as exception:
        raise ValueError(f"invalid baseline report: {path}") from exception


def main(arguments: Sequence[str] | None = None) -> int:
    options = _parser().parse_args(arguments)
    try:
        dataset, fingerprint = load_evaluation_dataset(options.dataset)
        report = run_evaluation(
            dataset,
            fingerprint,
            thresholds=_load_thresholds(options.thresholds),
        )
        write_report(report, options.output)
        tracker = (
            MlflowEvaluationTracker()
            if options.track_mlflow
            else NullEvaluationTracker()
        )
        tracker.record(report)
        comparison = (
            compare_reports(
                _load_report(options.baseline_report),
                report,
                tolerance=options.regression_tolerance,
            )
            if options.baseline_report is not None
            else None
        )
        enforce_release_gate(report, comparison)
    except (ValueError, ReleaseGateError) as exception:
        print(f"EVALUATION FAILED: {exception}", file=sys.stderr)
        return 1
    print(
        f"EVALUATION PASSED: {report.dataset_id}@{report.dataset_version} "
        f"({len(report.cases)} cases)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
