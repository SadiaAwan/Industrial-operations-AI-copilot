"""Tests for bounded, machine-scoped Streamlit session state."""

from app.domain.common import Severity
from app.schemas.chat import ChatResponse
from app.schemas.recommendations import AgentRecommendation
from frontend.state import MAX_CHAT_MESSAGES, CopilotUIState, InteractionMetrics


def response(index: int) -> ChatResponse:
    return ChatResponse(
        request_id=f"REQ-{index}",
        session_id="SESSION-1",
        result=AgentRecommendation(
            machine_id="P-104",
            current_condition="Stable",
            severity=Severity.NORMAL,
            confidence=0.9,
            observations=(),
            possible_causes=(),
            recommended_checks=(),
            safety_notice="Follow approved procedures.",
        ),
    )


def test_chat_history_is_bounded_and_preserves_latest_turns() -> None:
    state = CopilotUIState()
    metrics = InteractionMetrics(latency_ms=12.5)

    for index in range(MAX_CHAT_MESSAGES + 5):
        state.record_turn(f"Message {index}", response(index), metrics)

    assert len(state.turns) == MAX_CHAT_MESSAGES
    assert state.turns[0].response.request_id == "REQ-5"
    assert state.turns[-1].response.request_id == f"REQ-{MAX_CHAT_MESSAGES + 4}"


def test_machine_change_resets_machine_scoped_state() -> None:
    state = CopilotUIState()
    state.record_turn("Status", response(1), InteractionMetrics(latency_ms=1))
    state.mark_feedback_submitted("REQ-1")
    state.mark_action_decided("ACT-1")

    state.select_machine("P-205")

    assert state.selected_machine_id == "P-205"
    assert state.session_id is None
    assert state.turns == []
    assert state.submitted_feedback_request_ids == set()
    assert state.decided_action_ids == set()


def test_selecting_same_machine_preserves_session() -> None:
    state = CopilotUIState()
    state.record_turn("Status", response(1), InteractionMetrics(latency_ms=1))

    state.select_machine("P-101")

    assert state.session_id == "SESSION-1"
    assert len(state.turns) == 1
