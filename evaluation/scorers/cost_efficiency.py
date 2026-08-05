"""Per-request cost-budget scorer."""

from evaluation.scorers.contracts import EvaluationResult, MetricScore


def score_cost_efficiency(
    result: EvaluationResult, *, maximum_cost_usd: float = 0.10
) -> MetricScore:
    if maximum_cost_usd <= 0:
        raise ValueError("maximum_cost_usd must be positive")
    value = min(
        1.0,
        maximum_cost_usd / max(result.estimated_cost_usd, maximum_cost_usd),
    )
    return MetricScore(
        metric="cost_efficiency",
        value=value,
        threshold=1.0,
        passed=result.estimated_cost_usd <= maximum_cost_usd,
        details={
            "estimated_cost_usd": result.estimated_cost_usd,
            "maximum_cost_usd": maximum_cost_usd,
        },
    )
