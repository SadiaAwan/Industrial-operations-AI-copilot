"""Tests for bounded, session-isolated agent memory."""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from app.agent.memory import (
    InMemorySessionMemory,
    capture_session,
    restore_session,
)
from app.agent.state import AgentState, initial_agent_state
from app.schemas.tools import SensorReadingOutput

NOW = datetime(2026, 8, 2, 10, 0, tzinfo=UTC)


def _state(
    session_id: str,
    machine_id: str | None = "P-104",
) -> AgentState:
    state = initial_agent_state(
        message="Continue troubleshooting",
        session_id=session_id,
        machine_id=machine_id,
        started_at=NOW,
    )
    state["sensor_data"] = (
        SensorReadingOutput(
            reading_id="SR-1",
            machine_id="P-104",
            sensor_type="vibration_rms",
            value=7.2,
            unit="mm/s RMS",
            recorded_at=NOW,
        ),
    )
    return state


def test_snapshot_restores_bounded_evidence_for_same_session() -> None:
    snapshot = capture_session(_state("S-1"), updated_at=NOW)
    fresh = _state("S-1", machine_id=None)
    fresh["sensor_data"] = ()

    restored = restore_session(fresh, snapshot)

    assert restored["machine_id"] == "P-104"
    assert restored["sensor_data"][0].reading_id == "SR-1"
    assert restored["errors"] == ()
    assert restored["recommendation"] is None


def test_snapshot_cannot_cross_session_boundary() -> None:
    snapshot = capture_session(_state("S-1"), updated_at=NOW)

    with pytest.raises(ValueError, match="another session"):
        restore_session(_state("S-2"), snapshot)


def test_in_memory_store_evicts_oldest_session_at_limit() -> None:
    async def exercise() -> None:
        memory = InMemorySessionMemory(max_sessions=2)
        await memory.save(capture_session(_state("S-1"), updated_at=NOW))
        await memory.save(
            capture_session(_state("S-2"), updated_at=NOW + timedelta(seconds=1))
        )
        await memory.save(
            capture_session(_state("S-3"), updated_at=NOW + timedelta(seconds=2))
        )

        assert await memory.load("S-1") is None
        assert await memory.load("S-2") is not None
        assert await memory.load("S-3") is not None

    asyncio.run(exercise())


def test_empty_session_identifier_is_rejected() -> None:
    with pytest.raises(ValueError, match="session_id"):
        asyncio.run(InMemorySessionMemory().load(" "))
