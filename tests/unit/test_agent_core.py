"""Unit tests for agent state, routing, and structured generation."""

import asyncio
from datetime import UTC, datetime

import pytest

from app.agent.model import (
    DeterministicRecommendationGenerator,
    RecommendationContext,
)
from app.agent.routing import classify_intent, extract_machine_id
from app.agent.state import AgentIntent, initial_agent_state
from app.retrieval.citations import Citation
from app.schemas.tools import (
    DocumentSearchOutput,
    IncidentOutput,
    SensorReadingOutput,
)

NOW = datetime(2026, 8, 2, 10, 0, tzinfo=UTC)


def test_initial_state_is_bounded_and_empty() -> None:
    state = initial_agent_state(
        message="Diagnose P-104",
        session_id="S-1",
        machine_id=None,
        started_at=NOW,
    )

    assert state["max_steps"] == 20
    assert state["sensor_window_hours"] == 4
    assert state["documents"] == ()
    assert state["errors"] == ()


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("Diagnose pump P-104", "P-104"),
        ("status for p-105 please", "P-105"),
        ("No machine supplied", None),
    ],
)
def test_machine_id_extraction(message: str, expected: str | None) -> None:
    assert extract_machine_id(message) == expected


def test_work_order_intent_takes_precedence_over_sensor_terms() -> None:
    intent = classify_intent("Create a work order draft for high vibration on P-104")

    assert intent == AgentIntent.WORK_ORDER_DRAFT


def test_deterministic_generator_separates_evidence_and_hypotheses() -> None:
    context = RecommendationContext(
        machine_id="P-104",
        message="P-104 has high vibration and temperature",
        intent=AgentIntent.DIAGNOSTIC,
        sensor_data=(
            SensorReadingOutput(
                reading_id="SR-VIB",
                machine_id="P-104",
                sensor_type="vibration_rms",
                value=7.2,
                unit="mm/s RMS",
                recorded_at=NOW,
            ),
            SensorReadingOutput(
                reading_id="SR-TEMP",
                machine_id="P-104",
                sensor_type="bearing_temperature",
                value=82.0,
                unit="°C",
                recorded_at=NOW,
            ),
        ),
        documents=(
            DocumentSearchOutput(
                content="Rising vibration and temperature can indicate bearing wear.",
                score=0.9,
                citation=Citation(
                    chunk_id="CH-7-3",
                    document_id="pump_manual_v2",
                    title="Pump manual",
                    revision="2.1",
                    section="7.3 Bearings",
                    source_path="manuals/pump.md",
                    excerpt="Rising vibration and temperature.",
                ),
            ),
        ),
        incidents=(
            IncidentOutput(
                incident_id="INC-014",
                machine_id="P-104",
                occurred_at=NOW,
                severity="high",
                summary="Similar vibration and temperature trend.",
                root_cause="bearing degradation",
                resolution="Bearing replaced.",
            ),
        ),
    )

    result = asyncio.run(DeterministicRecommendationGenerator().generate(context))

    assert result.possible_causes[0].cause == "bearing degradation"
    assert result.possible_causes[0].confidence >= 0.8
    assert any(item.source_type == "sensor" for item in result.observations)
    assert result.citations[0].chunk_id == "CH-7-3"
    assert result.requires_human_approval is False
    assert result.recommended_checks[0].safety_critical is True
