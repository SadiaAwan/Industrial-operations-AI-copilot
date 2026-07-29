"""Generate deterministic synthetic data for the centrifugal-pump MVP."""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from app.domain.common import MachineStatus, Severity
from app.domain.incident import Incident
from app.domain.machine import Machine
from app.domain.maintenance_record import MaintenanceRecord
from app.domain.sensor_reading import (
    EXPECTED_UNITS,
    SensorReading,
    SensorType,
)

DEFAULT_SEED = 104
REFERENCE_TIME = datetime(2026, 7, 23, 10, 0, tzinfo=UTC)

MACHINE_SCENARIOS: tuple[tuple[Machine, str], ...] = (
    (
        Machine(
            machine_id="P-101",
            name="Cooling Water Pump 1",
            machine_type="centrifugal_pump",
            status=MachineStatus.ACTIVE,
            location="Utilities / Cooling loop A",
        ),
        "normal",
    ),
    (
        Machine(
            machine_id="P-102",
            name="Process Feed Pump 2",
            machine_type="centrifugal_pump",
            status=MachineStatus.ACTIVE,
            location="Process Area / Feed train",
        ),
        "cavitation",
    ),
    (
        Machine(
            machine_id="P-103",
            name="Transfer Pump 3",
            machine_type="centrifugal_pump",
            status=MachineStatus.MAINTENANCE,
            location="Tank Farm / Transfer line",
        ),
        "misalignment",
    ),
    (
        Machine(
            machine_id="P-104",
            name="Cooling Water Pump 4",
            machine_type="centrifugal_pump",
            status=MachineStatus.ACTIVE,
            location="Utilities / Cooling loop B",
        ),
        "bearing_degradation",
    ),
    (
        Machine(
            machine_id="P-105",
            name="Booster Pump 5",
            machine_type="centrifugal_pump",
            status=MachineStatus.ACTIVE,
            location="Distribution / Booster station",
        ),
        "overload",
    ),
)

ROOT_CAUSES: tuple[tuple[str, str, Severity, str], ...] = (
    (
        "bearing degradation",
        "Rising drive-end vibration and bearing temperature",
        Severity.HIGH,
        "Bearing replaced and shaft alignment verified",
    ),
    (
        "cavitation",
        "Fluctuating vibration, low suction pressure, and reduced flow",
        Severity.HIGH,
        "Inlet restriction removed and suction conditions restored",
    ),
    (
        "shaft misalignment",
        "Elevated vibration after coupling maintenance",
        Severity.MEDIUM,
        "Motor and pump shafts realigned",
    ),
    (
        "motor overload",
        "High motor current with reduced rotational speed",
        Severity.HIGH,
        "Process load reduced and motor protection inspected",
    ),
    (
        "blocked strainer",
        "Falling suction pressure and flow rate",
        Severity.MEDIUM,
        "Suction strainer isolated and cleaned",
    ),
)

MAINTENANCE_TYPES: tuple[tuple[str, str], ...] = (
    ("preventive inspection", "Inspected seals, bearings, coupling, and baseplate."),
    ("lubrication", "Verified lubricant condition and replenished to specified level."),
    ("alignment check", "Measured shaft alignment and recorded coupling offsets."),
    (
        "bearing replacement",
        "Replaced drive-end bearing and verified running condition.",
    ),
    ("seal inspection", "Inspected mechanical seal and checked for visible leakage."),
)


def _rounded(value: float, digits: int = 2) -> float:
    return round(max(value, 0.01), digits)


def _scenario_values(
    scenario: str,
    progress: float,
    rng: random.Random,
) -> dict[SensorType, float]:
    def noise(scale: float) -> float:
        return rng.uniform(-scale, scale)

    values: dict[SensorType, float] = {
        SensorType.VIBRATION_RMS: 3.0 + noise(0.12),
        SensorType.BEARING_TEMPERATURE: 66.0 + noise(0.5),
        SensorType.MOTOR_CURRENT: 23.0 + noise(0.25),
        SensorType.SUCTION_PRESSURE: 1.85 + noise(0.03),
        SensorType.DISCHARGE_PRESSURE: 5.6 + noise(0.05),
        SensorType.FLOW_RATE: 114.0 + noise(1.0),
        SensorType.ROTATIONAL_SPEED: 1_480.0 + noise(2.0),
    }

    if scenario == "cavitation":
        values.update(
            {
                SensorType.VIBRATION_RMS: 3.2 + 3.4 * progress + noise(0.18),
                SensorType.BEARING_TEMPERATURE: 67.0 + 5.0 * progress + noise(0.5),
                SensorType.SUCTION_PRESSURE: 1.8 - 0.75 * progress + noise(0.03),
                SensorType.DISCHARGE_PRESSURE: 5.5 - 0.9 * progress + noise(0.05),
                SensorType.FLOW_RATE: 113.0 - 27.0 * progress + noise(1.0),
            }
        )
    elif scenario == "misalignment":
        values.update(
            {
                SensorType.VIBRATION_RMS: 3.0 + 4.0 * progress + noise(0.12),
                SensorType.BEARING_TEMPERATURE: 66.0 + 8.0 * progress + noise(0.4),
                SensorType.MOTOR_CURRENT: 23.0 + 1.8 * progress + noise(0.2),
            }
        )
    elif scenario == "bearing_degradation":
        values.update(
            {
                SensorType.VIBRATION_RMS: 3.1 + 4.1 * progress + noise(0.06),
                SensorType.BEARING_TEMPERATURE: 67.0 + 15.0 * progress + noise(0.25),
                SensorType.MOTOR_CURRENT: 23.4 + 2.4 * progress + noise(0.18),
                SensorType.SUCTION_PRESSURE: 1.8 - 0.6 * progress + noise(0.02),
                SensorType.DISCHARGE_PRESSURE: 5.6 - 0.65 * progress + noise(0.04),
                SensorType.FLOW_RATE: 114.0 - 23.0 * progress + noise(0.7),
            }
        )
    elif scenario == "overload":
        values.update(
            {
                SensorType.VIBRATION_RMS: 3.0 + 1.8 * progress + noise(0.1),
                SensorType.BEARING_TEMPERATURE: 66.0 + 11.0 * progress + noise(0.4),
                SensorType.MOTOR_CURRENT: 23.0 + 9.0 * progress + noise(0.25),
                SensorType.ROTATIONAL_SPEED: 1_480.0 - 55.0 * progress + noise(2.0),
            }
        )

    return {sensor_type: _rounded(value) for sensor_type, value in values.items()}


def generate_sensor_readings(
    seed: int = DEFAULT_SEED,
    samples_per_machine: int = 12,
) -> list[SensorReading]:
    """Return deterministic long-form readings for all MVP machines."""

    if samples_per_machine < 2:
        raise ValueError("samples_per_machine must be at least 2")

    rng = random.Random(seed)
    readings: list[SensorReading] = []
    for machine, scenario in MACHINE_SCENARIOS:
        for sample_index in range(samples_per_machine):
            recorded_at = REFERENCE_TIME + timedelta(minutes=sample_index * 5)
            progress = sample_index / (samples_per_machine - 1)
            values = _scenario_values(scenario, progress, rng)
            for sensor_type, value in values.items():
                readings.append(
                    SensorReading(
                        reading_id=(
                            f"SR-{machine.machine_id}-{sample_index:03d}-"
                            f"{sensor_type.value}"
                        ),
                        machine_id=machine.machine_id,
                        sensor_type=sensor_type,
                        value=value,
                        unit=EXPECTED_UNITS[sensor_type],
                        recorded_at=recorded_at,
                    )
                )
    return readings


def generate_incidents(
    seed: int = DEFAULT_SEED,
    count: int = 30,
) -> list[Incident]:
    """Return deterministic historical incidents."""

    if count < 1:
        raise ValueError("count must be positive")

    rng = random.Random(seed + 1)
    incidents: list[Incident] = []
    for index in range(count):
        machine, _ = MACHINE_SCENARIOS[index % len(MACHINE_SCENARIOS)]
        cause, symptom, severity, resolution = ROOT_CAUSES[index % len(ROOT_CAUSES)]
        occurred_at = REFERENCE_TIME - timedelta(
            days=35 + index * 17,
            hours=rng.randint(0, 12),
        )
        incidents.append(
            Incident(
                incident_id=f"INC-{index + 1:03d}",
                machine_id=machine.machine_id,
                occurred_at=occurred_at,
                severity=severity,
                summary=f"{symptom}. Confirmed cause: {cause}.",
                root_cause=cause,
                resolution=resolution,
            )
        )
    return incidents


def generate_maintenance_records(
    seed: int = DEFAULT_SEED,
    count: int = 75,
) -> list[MaintenanceRecord]:
    """Return deterministic maintenance history."""

    if count < 1:
        raise ValueError("count must be positive")

    rng = random.Random(seed + 2)
    records: list[MaintenanceRecord] = []
    for index in range(count):
        machine, _ = MACHINE_SCENARIOS[index % len(MACHINE_SCENARIOS)]
        maintenance_type, description = MAINTENANCE_TYPES[
            index % len(MAINTENANCE_TYPES)
        ]
        performed_at = REFERENCE_TIME - timedelta(
            days=14 + index * 9,
            hours=rng.randint(0, 8),
        )
        records.append(
            MaintenanceRecord(
                record_id=f"MR-{index + 1:03d}",
                machine_id=machine.machine_id,
                performed_at=performed_at,
                maintenance_type=maintenance_type,
                description=description,
                technician_id=f"TECH-{(index % 8) + 1:03d}",
            )
        )
    return records


def _json_ready(items: Sequence[Any]) -> list[dict[str, Any]]:
    return [item.model_dump(mode="json") for item in items]


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _write_sensor_csv(path: Path, readings: Sequence[SensorReading]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=(
                "reading_id",
                "machine_id",
                "sensor_type",
                "value",
                "unit",
                "recorded_at",
            ),
        )
        writer.writeheader()
        for reading in readings:
            writer.writerow(reading.model_dump(mode="json"))


def generate_dataset(output_root: Path, seed: int = DEFAULT_SEED) -> None:
    """Generate all structured phase-2 data below ``output_root``."""

    machines = [machine for machine, _ in MACHINE_SCENARIOS]
    scenario_map = {
        machine.machine_id: scenario for machine, scenario in MACHINE_SCENARIOS
    }
    readings = generate_sensor_readings(seed=seed)
    incidents = generate_incidents(seed=seed)
    maintenance = generate_maintenance_records(seed=seed)

    _write_json(
        output_root / "machines" / "machines.json",
        {
            "seed": seed,
            "generated_at": REFERENCE_TIME.isoformat(),
            "machines": _json_ready(machines),
            "scenario_by_machine": scenario_map,
        },
    )
    _write_sensor_csv(
        output_root / "synthetic_sensor_data" / "sensor_readings.csv",
        readings,
    )
    _write_json(
        output_root / "incidents" / "incidents.json",
        {"seed": seed, "incidents": _json_ready(incidents)},
    )
    _write_json(
        output_root / "maintenance" / "maintenance_records.json",
        {"seed": seed, "maintenance_records": _json_ready(maintenance)},
    )
    _write_json(
        output_root / "synthetic_sensor_data" / "invalid_readings.json",
        {
            "purpose": "Negative validation fixtures; never load as operational data.",
            "readings": [
                {
                    "case": "wrong_unit",
                    "machine_id": "P-104",
                    "sensor_type": "bearing_temperature",
                    "value": 82.0,
                    "unit": "bar",
                    "recorded_at": "2026-07-23T10:55:00Z",
                },
                {
                    "case": "naive_timestamp",
                    "machine_id": "P-104",
                    "sensor_type": "vibration_rms",
                    "value": 7.2,
                    "unit": "mm/s RMS",
                    "recorded_at": "2026-07-23T10:55:00",
                },
                {
                    "case": "unknown_machine",
                    "machine_id": "P-999",
                    "sensor_type": "motor_current",
                    "value": 25.8,
                    "unit": "A",
                    "recorded_at": "2026-07-23T10:55:00Z",
                },
            ],
        },
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    generate_dataset(args.output_root, seed=args.seed)


if __name__ == "__main__":
    main()
