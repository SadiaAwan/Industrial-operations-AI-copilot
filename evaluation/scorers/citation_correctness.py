"""Citation precision scorer with a zero-fabrication release threshold."""

from evaluation.scorers.contracts import EvaluationResult, MetricScore, normalized


def score_citation_correctness(
    result: EvaluationResult, *, threshold: float = 1.0
) -> MetricScore:
    expected = normalized(result.expected_citations)
    actual = normalized(result.actual_citations)
    valid = actual & expected
    fabricated = actual - expected
    value = len(valid) / len(actual) if actual else (1.0 if not expected else 0.0)
    return MetricScore(
        metric="citation_correctness",
        value=value,
        threshold=threshold,
        passed=value >= threshold,
        critical=True,
        details={
            "fabricated_citations": tuple(sorted(fabricated)),
            "missing_citations": tuple(sorted(expected - actual)),
        },
    )
