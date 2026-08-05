"""Groundedness scorer based on explicit claim-to-evidence judgments."""

from evaluation.scorers.contracts import EvaluationResult, MetricScore


def score_groundedness(
    result: EvaluationResult, *, threshold: float = 0.95
) -> MetricScore:
    claims = result.claims
    supported = sum(
        claim.supported and bool(claim.source_references) for claim in claims
    )
    value = supported / len(claims) if claims else 1.0
    unsupported = tuple(claim.claim for claim in claims if not claim.supported)
    return MetricScore(
        metric="groundedness",
        value=value,
        threshold=threshold,
        passed=value >= threshold,
        details={"unsupported_claims": unsupported, "claim_count": len(claims)},
    )
