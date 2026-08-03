"""LangGraph node implementations bound to validated phase-5 tools."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from app.agent.failures import (
    AgentStepLimitError,
    next_step,
    outcome_for_tool_error,
    tool_summary,
    uncertainty_message,
)
from app.agent.guardrails import GuardrailEngine, GuardrailViolation
from app.agent.model import RecommendationContext, RecommendationGenerator
from app.agent.routing import classify_intent, extract_machine_id
from app.agent.state import AgentIntent, AgentOutcome, AgentState
from app.domain.common import Severity
from app.schemas.recommendations import AgentRecommendation, RecommendedCheck
from app.schemas.tools import (
    DocumentSearchQuery,
    IncidentSearchQuery,
    MachineQuery,
    SensorDataQuery,
    ToolError,
    ToolErrorCode,
    WorkOrderDraftRequest,
)
from app.tools.document_search import DocumentSearchTool
from app.tools.incident_search import IncidentSearchTool
from app.tools.maintenance_history import MaintenanceHistoryTool
from app.tools.sensor_reader import SensorDataTool
from app.tools.work_order import WorkOrderDraftTool

StateUpdate = dict[str, object]


@dataclass(frozen=True, slots=True)
class AgentDependencies:
    sensor_tool: SensorDataTool
    document_tool: DocumentSearchTool
    incident_tool: IncidentSearchTool
    maintenance_tool: MaintenanceHistoryTool
    work_order_tool: WorkOrderDraftTool
    recommendation_generator: RecommendationGenerator
    guardrails: GuardrailEngine = field(default_factory=GuardrailEngine)


class AgentNodes:
    def __init__(self, dependencies: AgentDependencies) -> None:
        self._dependencies = dependencies

    @staticmethod
    def _step(state: AgentState) -> int:
        return next_step(state)

    @staticmethod
    def _failure(
        *,
        state: AgentState,
        tool_name: str,
        error: ToolError,
    ) -> StateUpdate:
        return {
            "step_count": next_step(state),
            "errors": (error,),
            "tool_calls": (tool_summary(tool_name, error),),
            "outcome": outcome_for_tool_error(error),
        }

    def validate_request(self, state: AgentState) -> StateUpdate:
        try:
            step = self._step(state)
        except AgentStepLimitError:
            return {
                "outcome": AgentOutcome.LOOP_LIMIT_REACHED,
                "clarification_required": False,
            }
        try:
            self._dependencies.guardrails.validate_request(state["message"])
        except GuardrailViolation as violation:
            return {
                "step_count": step,
                "clarification_required": False,
                "outcome": AgentOutcome.SAFETY_BLOCKED,
                "safety_message": f"Request blocked by safety policy: {violation.code}",
            }
        machine_id = state["machine_id"] or extract_machine_id(state["message"])
        return {
            "step_count": step,
            "machine_id": machine_id,
            "clarification_required": machine_id is None,
            "outcome": (
                AgentOutcome.CLARIFICATION_REQUIRED if machine_id is None else None
            ),
        }

    def classify_request(self, state: AgentState) -> StateUpdate:
        return {
            "step_count": self._step(state),
            "intent": classify_intent(state["message"]),
        }

    async def read_sensor_data(self, state: AgentState) -> StateUpdate:
        machine_id = self._required_machine(state)
        end_at = state["started_at"]
        request = SensorDataQuery(
            machine_id=machine_id,
            start_at=end_at - timedelta(hours=state["sensor_window_hours"]),
            end_at=end_at,
            limit=100,
        )
        result = await self._dependencies.sensor_tool(request)
        if result.error is not None:
            return self._failure(
                state=state,
                tool_name=self._dependencies.sensor_tool.name,
                error=result.error,
            )
        return {
            "step_count": self._step(state),
            "sensor_data": result.data or (),
            "tool_calls": (tool_summary(self._dependencies.sensor_tool.name, None),),
        }

    async def search_documents(self, state: AgentState) -> StateUpdate:
        request = DocumentSearchQuery(
            query=state["message"],
            machine_type="centrifugal_pump",
            limit=5,
        )
        result = await self._dependencies.document_tool(request)
        if result.error is not None:
            return self._failure(
                state=state,
                tool_name=self._dependencies.document_tool.name,
                error=result.error,
            )
        return {
            "step_count": self._step(state),
            "documents": result.data or (),
            "tool_calls": (tool_summary(self._dependencies.document_tool.name, None),),
        }

    async def search_incidents(self, state: AgentState) -> StateUpdate:
        request = IncidentSearchQuery(
            machine_id=self._required_machine(state),
            query=state["message"][:500],
            limit=10,
        )
        result = await self._dependencies.incident_tool(request)
        if result.error is not None:
            return self._failure(
                state=state,
                tool_name=self._dependencies.incident_tool.name,
                error=result.error,
            )
        return {
            "step_count": self._step(state),
            "incidents": result.data or (),
            "tool_calls": (tool_summary(self._dependencies.incident_tool.name, None),),
        }

    async def read_maintenance(self, state: AgentState) -> StateUpdate:
        request = MachineQuery(
            machine_id=self._required_machine(state),
            limit=10,
        )
        result = await self._dependencies.maintenance_tool(request)
        if result.error is not None:
            return self._failure(
                state=state,
                tool_name=self._dependencies.maintenance_tool.name,
                error=result.error,
            )
        return {
            "step_count": self._step(state),
            "maintenance": result.data or (),
            "tool_calls": (
                tool_summary(self._dependencies.maintenance_tool.name, None),
            ),
        }

    def assess_evidence(self, state: AgentState) -> StateUpdate:
        intent = state["intent"]
        sufficient = {
            AgentIntent.SENSOR_STATUS: bool(state["sensor_data"]),
            AgentIntent.INCIDENT_SEARCH: bool(state["incidents"]),
            AgentIntent.MAINTENANCE_HISTORY: bool(state["maintenance"]),
            AgentIntent.SAFETY_PROCEDURE: bool(state["documents"]),
            AgentIntent.DIAGNOSTIC: bool(state["sensor_data"])
            and bool(state["documents"] or state["incidents"]),
            AgentIntent.WORK_ORDER_DRAFT: bool(state["sensor_data"])
            and bool(state["documents"] or state["incidents"]),
        }[intent]
        return {
            "step_count": self._step(state),
            "evidence_sufficient": sufficient,
            "outcome": (None if sufficient else AgentOutcome.INSUFFICIENT_EVIDENCE),
        }

    async def generate_recommendation(self, state: AgentState) -> StateUpdate:
        try:
            self._dependencies.guardrails.validate_documents(state["documents"])
        except GuardrailViolation as violation:
            return {
                "step_count": self._step(state),
                "outcome": AgentOutcome.SAFETY_BLOCKED,
                "safety_message": (
                    f"Retrieved evidence blocked by safety policy: {violation.code}"
                ),
            }
        context = RecommendationContext(
            machine_id=self._required_machine(state),
            message=state["message"],
            intent=state["intent"],
            sensor_data=state["sensor_data"],
            documents=state["documents"],
            incidents=state["incidents"],
            maintenance=state["maintenance"],
        )
        try:
            recommendation = await self._dependencies.recommendation_generator.generate(
                context
            )
        except Exception:
            error = ToolError(
                code=ToolErrorCode.INTERNAL_ERROR,
                message="recommendation generation failed safely",
            )
            return {
                "step_count": self._step(state),
                "errors": (error,),
                "outcome": AgentOutcome.TOOL_FAILURE,
            }
        try:
            self._dependencies.guardrails.validate_recommendation(
                recommendation,
                documents=state["documents"],
            )
        except GuardrailViolation as violation:
            return {
                "step_count": self._step(state),
                "outcome": AgentOutcome.SAFETY_BLOCKED,
                "safety_message": (
                    f"Recommendation blocked by safety policy: {violation.code}"
                ),
            }
        return {
            "step_count": self._step(state),
            "recommendation": recommendation.model_copy(
                update={"tool_calls": state["tool_calls"]}
            ),
            "outcome": AgentOutcome.COMPLETED,
        }

    async def create_work_order_draft(self, state: AgentState) -> StateUpdate:
        recommendation = state["recommendation"]
        if recommendation is None:
            raise ValueError("recommendation required before work-order draft")
        checks = tuple(check.instruction for check in recommendation.recommended_checks)
        request = WorkOrderDraftRequest(
            machine_id=self._required_machine(state),
            title=f"Inspect {self._required_machine(state)}",
            description=(
                f"Diagnostic draft based on: {recommendation.current_condition}"
            ),
            priority=recommendation.severity,
            proposed_checks=checks,
        )
        result = await self._dependencies.work_order_tool(request)
        if result.error is not None:
            return self._failure(
                state=state,
                tool_name=self._dependencies.work_order_tool.name,
                error=result.error,
            )
        draft = result.data
        assert draft is not None
        calls = state["tool_calls"] + (
            tool_summary(self._dependencies.work_order_tool.name, None),
        )
        return {
            "step_count": self._step(state),
            "proposed_action": draft,
            "tool_calls": (
                tool_summary(self._dependencies.work_order_tool.name, None),
            ),
            "recommendation": recommendation.model_copy(
                update={
                    "requires_human_approval": True,
                    "proposed_action": draft,
                    "tool_calls": calls,
                }
            ),
            "outcome": AgentOutcome.COMPLETED,
        }

    def finalize(self, state: AgentState) -> StateUpdate:
        update: StateUpdate = {"step_count": self._step(state)}
        if state["recommendation"] is not None or state["machine_id"] is None:
            return update
        update["recommendation"] = AgentRecommendation(
            machine_id=state["machine_id"],
            current_condition=uncertainty_message(state),
            severity=Severity.NORMAL,
            confidence=0.0,
            observations=(),
            possible_causes=(),
            recommended_checks=(
                RecommendedCheck(
                    instruction="Verify the machine and required data sources.",
                    rationale="A grounded diagnosis requires sufficient evidence.",
                    safety_critical=False,
                ),
            ),
            safety_notice=(
                "Do not perform physical inspection without the approved safety "
                "procedure and human authorization."
            ),
            tool_calls=state["tool_calls"],
        )
        return update

    def loop_limit(self, state: AgentState) -> StateUpdate:
        return {
            "outcome": AgentOutcome.LOOP_LIMIT_REACHED,
            "evidence_sufficient": False,
        }

    @staticmethod
    def _required_machine(state: AgentState) -> str:
        machine_id = state["machine_id"]
        if machine_id is None:
            raise ValueError("machine_id is required for this node")
        return machine_id
