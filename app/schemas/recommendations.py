"""Structured diagnostic output returned by the agent."""

from typing import Literal

from pydantic import Field, model_validator

from app.domain.common import Confidence, DomainModel, MachineId, Severity
from app.domain.work_order import WorkOrderDraft


class Observation(DomainModel):
    statement: str = Field(min_length=1)
    source_type: Literal["sensor", "document", "incident", "maintenance"]
    source_reference: str = Field(min_length=1)


class Hypothesis(DomainModel):
    cause: str = Field(min_length=1)
    confidence: Confidence
    supporting_observation_refs: tuple[str, ...] = ()


class RecommendedCheck(DomainModel):
    instruction: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    safety_critical: bool = False


class Citation(DomainModel):
    document_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    revision: str = Field(min_length=1)
    section: str = Field(min_length=1)
    chunk_id: str = Field(min_length=1)


class ToolCallSummary(DomainModel):
    tool_name: str = Field(min_length=1)
    status: Literal["succeeded", "failed", "timed_out"]


class AgentRecommendation(DomainModel):
    machine_id: MachineId
    current_condition: str = Field(min_length=1)
    severity: Severity
    confidence: Confidence
    observations: tuple[Observation, ...]
    possible_causes: tuple[Hypothesis, ...]
    recommended_checks: tuple[RecommendedCheck, ...]
    safety_notice: str = Field(min_length=1)
    citations: tuple[Citation, ...] = ()
    tool_calls: tuple[ToolCallSummary, ...] = ()
    requires_human_approval: bool = False
    proposed_action: WorkOrderDraft | None = None

    @model_validator(mode="after")
    def action_requires_approval(self) -> "AgentRecommendation":
        if (self.proposed_action is not None) != self.requires_human_approval:
            raise ValueError(
                "proposed_action and requires_human_approval must be set together"
            )
        return self
