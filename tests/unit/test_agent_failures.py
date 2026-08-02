"""Tests for bounded steps and stable agent failure behavior."""

from datetime import UTC, datetime

import pytest

from app.agent.failures import (
    AgentStepLimitError,
    next_step,
    outcome_for_tool_error,
    tool_status,
)
from app.agent.routing import route_after_validation
from app.agent.state import AgentOutcome, initial_agent_state
from app.schemas.tools import ToolError, ToolErrorCode

NOW = datetime(2026, 8, 2, 10, 0, tzinfo=UTC)


def test_step_budget_stops_additional_node_execution() -> None:
    state = initial_agent_state(
        message="Diagnose P-104",
        session_id="S-1",
        machine_id="P-104",
        started_at=NOW,
        max_steps=1,
    )
    state["step_count"] = 1

    assert route_after_validation(state) == "loop_limit"
    with pytest.raises(AgentStepLimitError, match="step limit"):
        next_step(state)


@pytest.mark.parametrize(
    ("code", "status", "outcome"),
    [
        (ToolErrorCode.TIMEOUT, "timed_out", AgentOutcome.TOOL_FAILURE),
        (ToolErrorCode.NOT_FOUND, "failed", AgentOutcome.MACHINE_NOT_FOUND),
        (
            ToolErrorCode.DEPENDENCY_UNAVAILABLE,
            "failed",
            AgentOutcome.TOOL_FAILURE,
        ),
    ],
)
def test_tool_errors_map_to_stable_agent_outcomes(
    code: ToolErrorCode,
    status: str,
    outcome: AgentOutcome,
) -> None:
    error = ToolError(code=code, message="safe failure")

    assert tool_status(error) == status
    assert outcome_for_tool_error(error) == outcome
