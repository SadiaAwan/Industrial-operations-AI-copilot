"""Tests for deterministic dashboard data transformations."""

from datetime import UTC, datetime, timedelta

from app.domain.common import MachineStatus
from app.domain.machine import Machine
from app.schemas.api import MachineStatusResponse
from app.schemas.tools import SensorReadingOutput
from frontend.components.dashboard import latest_sensor_values, sensor_rows

NOW = datetime(2026, 8, 4, 8, 0, tzinfo=UTC)


def machine_status() -> MachineStatusResponse:
    return MachineStatusResponse(
        machine=Machine(
            machine_id="P-104",
            name="Cooling Water Pump",
            machine_type="centrifugal_pump",
            status=MachineStatus.ACTIVE,
        ),
        latest_readings=(
            SensorReadingOutput(
                reading_id="R-1",
                machine_id="P-104",
                sensor_type="vibration",
                value=2.1,
                unit="mm/s",
                recorded_at=NOW - timedelta(minutes=5),
            ),
            SensorReadingOutput(
                reading_id="R-2",
                machine_id="P-104",
                sensor_type="vibration",
                value=2.4,
                unit="mm/s",
                recorded_at=NOW,
            ),
        ),
    )


def test_latest_sensor_values_uses_newest_reading() -> None:
    assert latest_sensor_values(machine_status()) == {"vibration": (2.4, "mm/s")}


def test_sensor_rows_preserve_units_and_timestamps() -> None:
    rows = sensor_rows(machine_status())

    assert len(rows) == 2
    assert rows[0]["timestamp"] == NOW - timedelta(minutes=5)
    assert rows[0]["unit"] == "mm/s"
