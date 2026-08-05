"""Tool-selection scorer for required and forbidden tool use."""

from evaluation.scorers.contracts import EvaluationResult, MetricScore, normalized


def score_tool_selection(
    result: EvaluationResult, *, threshold: float = 1.0
) -> MetricScore:
    expected = normalized(result.expected_tools)
    forbidden = normalized(result.forbidden_tools)
    actual = normalized(result.actual_tools)
    required_score = len(expected & actual) / len(expected) if expected else 1.0
    forbidden_score = 0.0 if actual & forbidden else 1.0
    value = (required_score + forbidden_score) / 2
    return MetricScore(
        metric="tool_selection",
        value=value,
        threshold=threshold,
        passed=value >= threshold,
        details={
            "missing_tools": tuple(sorted(expected - actual)),
            "forbidden_tools_used": tuple(sorted(actual & forbidden)),
        },
    )
