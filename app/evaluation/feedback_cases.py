"""Safe conversion of reviewed negative feedback into versioned eval cases."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime

from pydantic import Field, model_validator

from app.domain.common import FeedbackRating, require_utc
from app.evaluation.models import EvaluationModel


class FeedbackCaseInput(EvaluationModel):
    feedback_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    trace_id: str = Field(min_length=1)
    rating: FeedbackRating
    agent_version: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    prompt_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    reviewed: bool = False
    include_in_evaluation: bool = False
    case_id: str = Field(min_length=1)
    expected_outcome: str = Field(min_length=1)
    expected_causes: tuple[str, ...] = ()
    expected_citations: tuple[str, ...] = ()
    expected_tools: tuple[str, ...] = ()
    forbidden_tools: tuple[str, ...] = ()
    requires_human_approval: bool = False

    @model_validator(mode="after")
    def is_reviewed_negative_feedback(self) -> FeedbackCaseInput:
        if self.include_in_evaluation and not self.reviewed:
            raise ValueError("eval inclusion requires human review")
        if self.include_in_evaluation and self.rating != FeedbackRating.NOT_HELPFUL:
            raise ValueError("only reviewed negative feedback can seed eval cases")
        return self


class CuratedFeedbackCase(EvaluationModel):
    case_id: str
    source_feedback_id: str
    source_trace_id: str
    source_agent_version: str
    source_prompt_version: str
    source_prompt_sha256: str
    expected_outcome: str
    expected_causes: tuple[str, ...]
    expected_citations: tuple[str, ...]
    expected_tools: tuple[str, ...]
    forbidden_tools: tuple[str, ...]
    requires_human_approval: bool


class CuratedFeedbackDataset(EvaluationModel):
    dataset_id: str
    dataset_version: str
    generated_at: datetime
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    cases: tuple[CuratedFeedbackCase, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def case_ids_are_unique(self) -> CuratedFeedbackDataset:
        ids = [case.case_id for case in self.cases]
        if len(ids) != len(set(ids)):
            raise ValueError("curated feedback case IDs must be unique")
        require_utc(self.generated_at)
        return self


def curate_feedback_cases(
    records: tuple[FeedbackCaseInput, ...],
    *,
    dataset_id: str,
    dataset_version: str,
    generated_at: datetime,
) -> CuratedFeedbackDataset:
    """Create reviewed cases without copying sessions or user free text."""

    canonical_source = json.dumps(
        [record.model_dump(mode="json") for record in records],
        sort_keys=True,
        separators=(",", ":"),
    )
    cases = tuple(
        CuratedFeedbackCase(
            case_id=record.case_id,
            source_feedback_id=record.feedback_id,
            source_trace_id=record.trace_id,
            source_agent_version=record.agent_version,
            source_prompt_version=record.prompt_version,
            source_prompt_sha256=record.prompt_sha256,
            expected_outcome=record.expected_outcome,
            expected_causes=record.expected_causes,
            expected_citations=record.expected_citations,
            expected_tools=record.expected_tools,
            forbidden_tools=record.forbidden_tools,
            requires_human_approval=record.requires_human_approval,
        )
        for record in records
        if record.include_in_evaluation
    )
    return CuratedFeedbackDataset(
        dataset_id=dataset_id,
        dataset_version=dataset_version,
        generated_at=generated_at,
        source_sha256=hashlib.sha256(canonical_source.encode()).hexdigest(),
        cases=cases,
    )
