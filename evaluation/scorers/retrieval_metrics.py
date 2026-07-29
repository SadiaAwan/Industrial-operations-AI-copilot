"""Deterministic retrieval metrics used by local and CI evaluation."""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict, Field


class RetrievalMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    recall_at_k: float = Field(ge=0.0, le=1.0)
    precision_at_k: float = Field(ge=0.0, le=1.0)
    reciprocal_rank: float = Field(ge=0.0, le=1.0)
    matched_references: tuple[str, ...]


def reference_matches(expected: str, retrieved: str) -> bool:
    """Match exact references or a numbered section with its heading suffix."""

    normalized_expected = expected.casefold().strip()
    normalized_retrieved = retrieved.casefold().strip()
    return (
        normalized_retrieved == normalized_expected
        or normalized_retrieved.startswith(f"{normalized_expected} ")
    )


def score_retrieval(
    *,
    expected_references: Sequence[str],
    retrieved_references: Sequence[str],
    k: int,
) -> RetrievalMetrics:
    """Calculate Recall@k, Precision@k, and reciprocal rank."""

    if k < 1:
        raise ValueError("k must be positive")
    expected = tuple(dict.fromkeys(expected_references))
    if not expected:
        raise ValueError("expected_references must not be empty")
    retrieved = tuple(retrieved_references[:k])

    matched_expected = tuple(
        reference
        for reference in expected
        if any(reference_matches(reference, result) for result in retrieved)
    )
    relevant_results = sum(
        any(reference_matches(reference, result) for reference in expected)
        for result in retrieved
    )
    first_relevant_rank = next(
        (
            rank
            for rank, result in enumerate(retrieved, start=1)
            if any(reference_matches(reference, result) for reference in expected)
        ),
        None,
    )
    return RetrievalMetrics(
        recall_at_k=len(matched_expected) / len(expected),
        precision_at_k=relevant_results / k,
        reciprocal_rank=(
            1 / first_relevant_rank if first_relevant_rank is not None else 0.0
        ),
        matched_references=matched_expected,
    )
