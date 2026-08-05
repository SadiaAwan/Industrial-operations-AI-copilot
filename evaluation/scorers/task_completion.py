"""Task-completion scorer for outcome and diagnostic cause coverage."""

from evaluation.scorers.contracts import EvaluationResult, MetricScore, normalized


def score_task_completion(
    result: EvaluationResult, *, threshold: float = 0.8
) -> MetricScore:
    outcome_score = float(result.actual_outcome == result.expected_outcome)
    expected_causes = normalized(result.expected_causes)
    actual_causes = normalized(result.actual_causes)
    cause_score = (
        len(expected_causes & actual_causes) / len(expected_causes)
        if expected_causes
        else 1.0
    )
    value = (outcome_score + cause_score) / 2
    return MetricScore(
        metric="task_completion",
        value=value,
        threshold=threshold,
        passed=value >= threshold,
        details={
            "outcome_matched": bool(outcome_score),
            "missing_causes": tuple(sorted(expected_causes - actual_causes)),
        },
    )
