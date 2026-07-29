from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from app.domain import (
    AgentSession,
    ApprovalAction,
    Incident,
    Machine,
    MaintenanceRecord,
    SensorReading,
    WorkOrderDraft,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def test_valid_core_domain_objects() -> None:
    assert Machine(machine_id="P-104", name="Feed pump", machine_type="centrifugal")
    assert Incident(
        incident_id="INC-1",
        machine_id="P-104",
        occurred_at=NOW,
        severity="high",
        summary="Elevated vibration",
    )
    assert MaintenanceRecord(
        record_id="MR-1",
        machine_id="P-104",
        performed_at=NOW,
        maintenance_type="inspection",
        description="Bearing inspection",
    )
    assert AgentSession(
        session_id="S-1", machine_id="P-104", created_at=NOW, updated_at=NOW
    )


@pytest.mark.parametrize("machine_id", ["", "p-104", "P104", "P-1", "UNKNOWN"])
def test_invalid_machine_ids_are_rejected(machine_id: str) -> None:
    with pytest.raises(ValidationError):
        Machine(machine_id=machine_id, name="Pump", machine_type="centrifugal")


def test_sensor_unit_must_match_sensor_type() -> None:
    with pytest.raises(ValidationError, match="must use unit"):
        SensorReading(
            reading_id="R-1",
            machine_id="P-104",
            sensor_type="vibration_rms",
            value=4.2,
            unit="bar",
            recorded_at=NOW,
        )


def test_naive_timestamp_is_rejected() -> None:
    with pytest.raises(ValidationError, match="UTC"):
        Incident(
            incident_id="INC-1",
            machine_id="P-104",
            occurred_at=datetime(2026, 1, 1),
            severity="low",
            summary="Test",
        )


def test_unknown_status_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Machine(
            machine_id="P-104",
            name="Pump",
            machine_type="centrifugal",
            status="mystery",
        )


def test_draft_cannot_claim_work_was_executed() -> None:
    with pytest.raises(ValidationError, match="cannot represent"):
        WorkOrderDraft(
            draft_id="D-1",
            machine_id="P-104",
            title="Inspect pump",
            description="Inspect bearing",
            priority="high",
            status="completed",
        )


def test_approval_decision_requires_actor_and_timestamp() -> None:
    with pytest.raises(ValidationError, match="decision metadata"):
        ApprovalAction(
            action_id="A-1",
            session_id="S-1",
            requested_by="agent",
            action_type="create_work_order",
            payload={"draft_id": "D-1"},
            payload_hash="abc",
            status="approved",
            created_at=NOW,
            expires_at=NOW + timedelta(hours=1),
        )
