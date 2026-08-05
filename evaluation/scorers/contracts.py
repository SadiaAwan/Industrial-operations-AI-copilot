"""Shared immutable contracts for deterministic offline evaluation."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EvaluationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class ClaimEvidence(EvaluationModel):
    claim: str = Field(min_length=1)
    supported: bool
    source_references: tuple[str, ...] = ()


class EvaluationResult(EvaluationModel):
    case_id: str = Field(min_length=1)
    expected_outcome: str = Field(min_length=1)
    actual_outcome: str = Field(min_length=1)
    expected_causes: tuple[str, ...] = ()
    actual_causes: tuple[str, ...] = ()
    expected_citations: tuple[str, ...] = ()
    actual_citations: tuple[str, ...] = ()
    expected_tools: tuple[str, ...] = ()
    forbidden_tools: tuple[str, ...] = ()
    actual_tools: tuple[str, ...] = ()
    claims: tuple[ClaimEvidence, ...] = ()
    requires_human_approval: bool = False
    approval_present: bool = False
    write_attempted: bool = False
    latency_ms: float = Field(ge=0)
    estimated_cost_usd: float = Field(ge=0)

    @model_validator(mode="after")
    def approval_is_consistent(self) -> EvaluationResult:
        if self.approval_present and not self.requires_human_approval:
            raise ValueError("approval cannot be present for a read-only case")
        return self


class MetricScore(EvaluationModel):
    metric: str = Field(min_length=1)
    value: float = Field(ge=0, le=1)
    threshold: float = Field(ge=0, le=1)
    passed: bool
    critical: bool = False
    details: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def pass_matches_threshold(self) -> MetricScore:
        if self.passed != (self.value >= self.threshold):
            raise ValueError("passed must match value >= threshold")
        return self


def normalized(values: tuple[str, ...]) -> set[str]:
    return {value.casefold().strip() for value in values if value.strip()}
