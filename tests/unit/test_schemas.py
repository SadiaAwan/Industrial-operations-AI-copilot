from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.domain import WorkOrderDraft
from app.schemas.chat import ChatRequest
from app.schemas.recommendations import AgentRecommendation
from app.schemas.tools import MachineQuery, SensorDataQuery

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def test_tool_result_limits_are_bounded() -> None:
    with pytest.raises(ValidationError):
        MachineQuery(machine_id="P-104", limit=101)


def test_sensor_query_requires_utc_timestamps() -> None:
    with pytest.raises(ValidationError, match="UTC"):
        SensorDataQuery(
            machine_id="P-104",
            start_at=datetime(2026, 1, 1),
            end_at=NOW,
        )


def test_chat_request_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        ChatRequest(message="Status?", machine_id="P-104", unexpected=True)


def test_agent_output_separates_evidence_hypotheses_and_checks() -> None:
    result = AgentRecommendation(
        machine_id="P-104",
        current_condition="Elevated vibration",
        severity="high",
        confidence=0.8,
        observations=(
            {
                "statement": "Vibration is 8.1 mm/s RMS",
                "source_type": "sensor",
                "source_reference": "R-1",
            },
        ),
        possible_causes=(
            {
                "cause": "Bearing wear",
                "confidence": 0.6,
                "supporting_observation_refs": ("R-1",),
            },
        ),
        recommended_checks=(
            {
                "instruction": "Inspect bearing",
                "rationale": "Confirm the hypothesis",
            },
        ),
        safety_notice="Follow lockout/tagout before inspection.",
    )
    assert result.observations[0].statement != result.possible_causes[0].cause


def test_proposed_action_always_requires_human_approval() -> None:
    draft = WorkOrderDraft(
        draft_id="D-1",
        machine_id="P-104",
        title="Inspect pump",
        description="Inspect bearing",
        priority="high",
    )
    with pytest.raises(ValidationError, match="must be set together"):
        AgentRecommendation(
            machine_id="P-104",
            current_condition="Elevated vibration",
            severity="high",
            confidence=0.8,
            observations=(),
            possible_causes=(),
            recommended_checks=(),
            safety_notice="Follow lockout/tagout.",
            proposed_action=draft,
            requires_human_approval=False,
        )
