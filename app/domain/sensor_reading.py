"""Sensor measurement domain contracts."""

from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import Field, model_validator

from app.domain.common import DomainModel, MachineId, require_utc


class SensorType(StrEnum):
    VIBRATION_RMS = "vibration_rms"
    BEARING_TEMPERATURE = "bearing_temperature"
    MOTOR_CURRENT = "motor_current"
    SUCTION_PRESSURE = "suction_pressure"
    DISCHARGE_PRESSURE = "discharge_pressure"
    FLOW_RATE = "flow_rate"
    ROTATIONAL_SPEED = "rotational_speed"


class SensorUnit(StrEnum):
    MILLIMETERS_PER_SECOND_RMS = "mm/s RMS"
    CELSIUS = "°C"
    AMPERE = "A"
    BAR = "bar"
    CUBIC_METERS_PER_HOUR = "m³/h"
    REVOLUTIONS_PER_MINUTE = "rpm"


EXPECTED_UNITS: dict[SensorType, SensorUnit] = {
    SensorType.VIBRATION_RMS: SensorUnit.MILLIMETERS_PER_SECOND_RMS,
    SensorType.BEARING_TEMPERATURE: SensorUnit.CELSIUS,
    SensorType.MOTOR_CURRENT: SensorUnit.AMPERE,
    SensorType.SUCTION_PRESSURE: SensorUnit.BAR,
    SensorType.DISCHARGE_PRESSURE: SensorUnit.BAR,
    SensorType.FLOW_RATE: SensorUnit.CUBIC_METERS_PER_HOUR,
    SensorType.ROTATIONAL_SPEED: SensorUnit.REVOLUTIONS_PER_MINUTE,
}


class SensorReading(DomainModel):
    reading_id: str = Field(min_length=1)
    machine_id: MachineId
    sensor_type: SensorType
    value: Annotated[float, Field(allow_inf_nan=False)]
    unit: SensorUnit
    recorded_at: datetime

    @model_validator(mode="after")
    def validate_measurement(self) -> "SensorReading":
        require_utc(self.recorded_at)
        expected = EXPECTED_UNITS[self.sensor_type]
        if self.unit != expected:
            raise ValueError(f"{self.sensor_type} must use unit {expected}")
        return self
