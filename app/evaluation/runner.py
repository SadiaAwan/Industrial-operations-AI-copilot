"""Deterministic, provider-neutral evaluation suite runner."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime

from app.evaluation.models import (
    CaseEvaluation,
    EvaluationDataset,
    EvaluationReport,
    EvaluationThresholds,
)
from evaluation.scorers import (
    EvaluationResult,
    MetricScore,
    score_citation_correctness,
    score_cost_efficiency,
    score_groundedness,
    score_latency,
    score_task_completion,
    score_tool_behavior,
    score_tool_selection,
)


def score_case(
    result: EvaluationResult, thresholds: EvaluationThresholds
) -> CaseEvaluation:
    scores: tuple[MetricScore, ...] = (
        score_groundedness(result, threshold=thresholds.groundedness),
        score_citation_correctness(result, threshold=thresholds.citation_correctness),
        score_task_completion(result, threshold=thresholds.task_completion),
        score_tool_selection(result, threshold=thresholds.tool_selection),
        score_tool_behavior(result, threshold=thresholds.tool_behavior),
        score_latency(result, maximum_ms=thresholds.maximum_latency_ms),
        score_cost_efficiency(result, maximum_cost_usd=thresholds.maximum_cost_usd),
    )
    return CaseEvaluation(
        case_id=result.case_id,
        scores=scores,
        passed=all(score.passed for score in scores),
    )


def run_evaluation(
    dataset: EvaluationDataset,
    dataset_sha256: str,
    *,
    thresholds: EvaluationThresholds | None = None,
    generated_at: datetime | None = None,
) -> EvaluationReport:
    config = thresholds or EvaluationThresholds()
    cases = tuple(score_case(result, config) for result in dataset.results)
    values: defaultdict[str, list[float]] = defaultdict(list)
    for case in cases:
        for score in case.scores:
            values[score.metric].append(score.value)
    averages = {
        metric: sum(metric_values) / len(metric_values)
        for metric, metric_values in sorted(values.items())
    }
    return EvaluationReport(
        dataset_id=dataset.dataset_id,
        dataset_version=dataset.dataset_version,
        dataset_sha256=dataset_sha256,
        generated_at=generated_at or datetime.now(UTC),
        cases=cases,
        metric_averages=averages,
        passed=all(case.passed for case in cases),
    )
