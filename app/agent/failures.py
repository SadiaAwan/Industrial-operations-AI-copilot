"""Stable error mapping and loop-budget enforcement for agent nodes."""

from __future__ import annotations

from typing import Literal

from app.agent.state import AgentOutcome, AgentState
from app.schemas.recommendations import ToolCallSummary
from app.schemas.tools import ToolError, ToolErrorCode


class AgentStepLimitError(RuntimeError):
    """Raised when a node attempts to exceed the configured graph budget."""


def next_step(state: AgentState) -> int:
    step = state["step_count"] + 1
    if step > state["max_steps"]:
        raise AgentStepLimitError("agent step limit reached")
    return step


def tool_status(error: ToolError | None) -> Literal["succeeded", "failed", "timed_out"]:
    if error is None:
        return "succeeded"
    if error.code == ToolErrorCode.TIMEOUT:
        return "timed_out"
    return "failed"


def tool_summary(
    tool_name: str,
    error: ToolError | None,
) -> ToolCallSummary:
    return ToolCallSummary(tool_name=tool_name, status=tool_status(error))


def outcome_for_tool_error(error: ToolError) -> AgentOutcome:
    if error.code == ToolErrorCode.NOT_FOUND:
        return AgentOutcome.MACHINE_NOT_FOUND
    return AgentOutcome.TOOL_FAILURE


def uncertainty_message(state: AgentState) -> str:
    if state["outcome"] == AgentOutcome.MACHINE_NOT_FOUND:
        return f"Machine {state['machine_id']} was not found."
    if state["outcome"] == AgentOutcome.LOOP_LIMIT_REACHED:
        return "The diagnostic workflow stopped at its configured step limit."
    if state["errors"]:
        return (
            "The available evidence is incomplete because one or more data "
            "sources failed safely."
        )
    return "The available evidence is insufficient for a grounded recommendation."
