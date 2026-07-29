"""Tests for deterministic phase-2 data generation."""

import csv
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.domain.incident import Incident
from app.domain.machine import Machine
from app.domain.maintenance_record import MaintenanceRecord
from app.domain.sensor_reading import SensorReading
from scripts.generate_sensor_data import (
    MACHINE_SCENARIOS,
    generate_dataset,
    generate_incidents,
    generate_maintenance_records,
    generate_sensor_readings,
)


def test_generators_are_deterministic() -> None:
    assert generate_sensor_readings() == generate_sensor_readings()
    assert generate_incidents() == generate_incidents()
    assert generate_maintenance_records() == generate_maintenance_records()


def test_expected_dataset_sizes_and_machine_coverage() -> None:
    machine_ids = {machine.machine_id for machine, _ in MACHINE_SCENARIOS}
    readings = generate_sensor_readings()
    incidents = generate_incidents()
    maintenance = generate_maintenance_records()

    assert len(machine_ids) == 5
    assert len(readings) == 5 * 12 * 7
    assert len(incidents) == 30
    assert len(maintenance) == 75
    assert {item.machine_id for item in readings} == machine_ids
    assert {item.machine_id for item in incidents} == machine_ids
    assert {item.machine_id for item in maintenance} == machine_ids


def test_p104_bearing_scenario_has_clear_degradation_trend() -> None:
    readings = [
        item for item in generate_sensor_readings() if item.machine_id == "P-104"
    ]
    vibration = [item.value for item in readings if item.sensor_type == "vibration_rms"]
    temperature = [
        item.value for item in readings if item.sensor_type == "bearing_temperature"
    ]

    assert vibration[-1] - vibration[0] > 3.8
    assert temperature[-1] - temperature[0] > 14.0
    assert vibration[-1] >= 7.0
    assert temperature[-1] >= 81.5


def test_generated_files_round_trip_through_domain_models(
    tmp_path: Path,
) -> None:
    generate_dataset(tmp_path)

    machines_payload = json.loads(
        (tmp_path / "machines" / "machines.json").read_text(encoding="utf-8")
    )
    incidents_payload = json.loads(
        (tmp_path / "incidents" / "incidents.json").read_text(encoding="utf-8")
    )
    maintenance_payload = json.loads(
        (tmp_path / "maintenance" / "maintenance_records.json").read_text(
            encoding="utf-8"
        )
    )
    with (tmp_path / "synthetic_sensor_data" / "sensor_readings.csv").open(
        encoding="utf-8"
    ) as handle:
        readings_payload = list(csv.DictReader(handle))

    validated_machines = [
        Machine.model_validate(item) for item in machines_payload["machines"]
    ]
    assert len(validated_machines) == 5
    assert (
        len([Incident.model_validate(item) for item in incidents_payload["incidents"]])
        == 30
    )
    assert (
        len(
            [
                MaintenanceRecord.model_validate(item)
                for item in maintenance_payload["maintenance_records"]
            ]
        )
        == 75
    )
    assert len([SensorReading.model_validate(item) for item in readings_payload]) == 420


def test_negative_sensor_fixtures_are_rejected(tmp_path: Path) -> None:
    generate_dataset(tmp_path)
    payload = json.loads(
        (tmp_path / "synthetic_sensor_data" / "invalid_readings.json").read_text(
            encoding="utf-8"
        )
    )

    with pytest.raises(ValidationError):
        SensorReading.model_validate(payload["readings"][0])
    with pytest.raises(ValidationError):
        SensorReading.model_validate(payload["readings"][1])


@pytest.mark.parametrize("count", [0, -1])
def test_non_positive_record_counts_are_rejected(count: int) -> None:
    with pytest.raises(ValueError):
        generate_incidents(count=count)
    with pytest.raises(ValueError):
        generate_maintenance_records(count=count)


def test_sensor_generator_requires_multiple_samples() -> None:
    with pytest.raises(ValueError):
        generate_sensor_readings(samples_per_machine=1)
