"""Fail-open tracking adapter for aggregate evaluation metrics."""

from __future__ import annotations

from typing import Protocol

from app.evaluation.models import EvaluationReport


class EvaluationTracker(Protocol):
    def record(self, report: EvaluationReport) -> None: ...


class NullEvaluationTracker:
    def record(self, report: EvaluationReport) -> None:
        del report


class MlflowEvaluationTracker:
    def record(self, report: EvaluationReport) -> None:
        try:
            import mlflow  # type: ignore[import-not-found]

            with mlflow.start_run(run_name=f"evaluation-{report.dataset_version}"):
                mlflow.log_params(
                    {
                        "dataset_id": report.dataset_id,
                        "dataset_version": report.dataset_version,
                        "dataset_sha256": report.dataset_sha256,
                    }
                )
                mlflow.log_metrics(report.metric_averages)
                mlflow.set_tag("evaluation.passed", str(report.passed).lower())
        except Exception:
            # Tracking must not change the deterministic evaluation outcome.
            return
