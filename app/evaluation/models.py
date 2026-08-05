"""Evaluation suite configuration and report contracts."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.common import require_utc
from evaluation.scorers import EvaluationResult, MetricScore


class EvaluationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class EvaluationThresholds(EvaluationModel):
    groundedness: float = Field(default=0.95, ge=0, le=1)
    citation_correctness: float = Field(default=1.0, ge=0, le=1)
    task_completion: float = Field(default=0.8, ge=0, le=1)
    tool_selection: float = Field(default=1.0, ge=0, le=1)
    tool_behavior: float = Field(default=1.0, ge=0, le=1)
    maximum_latency_ms: float = Field(default=10_000, gt=0)
    maximum_cost_usd: float = Field(default=0.10, gt=0)


class EvaluationDataset(EvaluationModel):
    dataset_id: str = Field(min_length=1)
    dataset_version: str = Field(min_length=1)
    results: tuple[EvaluationResult, ...] = Field(min_length=1)


class CaseEvaluation(EvaluationModel):
    case_id: str = Field(min_length=1)
    scores: tuple[MetricScore, ...] = Field(min_length=1)
    passed: bool


class EvaluationReport(EvaluationModel):
    dataset_id: str = Field(min_length=1)
    dataset_version: str = Field(min_length=1)
    dataset_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    generated_at: datetime
    cases: tuple[CaseEvaluation, ...] = Field(min_length=1)
    metric_averages: dict[str, float]
    passed: bool

    @field_validator("generated_at")
    @classmethod
    def timestamp_is_utc(cls, value: datetime) -> datetime:
        return require_utc(value)
