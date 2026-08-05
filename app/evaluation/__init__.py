"""Public interfaces for offline evaluation and release gating."""

from app.evaluation.comparison import EvaluationComparison, compare_reports
from app.evaluation.datasets import EvaluationDatasetError, load_evaluation_dataset
from app.evaluation.models import (
    CaseEvaluation,
    EvaluationDataset,
    EvaluationReport,
    EvaluationThresholds,
)
from app.evaluation.reporting import render_report, write_report
from app.evaluation.runner import run_evaluation, score_case
from app.evaluation.tracking import (
    EvaluationTracker,
    MlflowEvaluationTracker,
    NullEvaluationTracker,
)

__all__ = [
    "CaseEvaluation",
    "EvaluationComparison",
    "EvaluationDataset",
    "EvaluationDatasetError",
    "EvaluationReport",
    "EvaluationThresholds",
    "EvaluationTracker",
    "MlflowEvaluationTracker",
    "NullEvaluationTracker",
    "compare_reports",
    "load_evaluation_dataset",
    "render_report",
    "run_evaluation",
    "score_case",
    "write_report",
]
