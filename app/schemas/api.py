"""Shared HTTP response contracts."""

from typing import Any, Literal

from pydantic import Field

from app.domain.common import DomainModel
from app.domain.machine import Machine
from app.schemas.tools import SensorReadingOutput


class APIErrorDetail(DomainModel):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    details: dict[str, Any] = Field(default_factory=dict)


class APIErrorResponse(DomainModel):
    error: APIErrorDetail


class MachineStatusResponse(DomainModel):
    machine: Machine
    latest_readings: tuple[SensorReadingOutput, ...] = ()


class DependencyStatus(DomainModel):
    name: str = Field(min_length=1)
    status: Literal["ready", "unavailable"]


class HealthResponse(DomainModel):
    status: Literal["ok"] = "ok"


class ReadinessResponse(DomainModel):
    status: Literal["ready", "not_ready"]
    dependencies: tuple[DependencyStatus, ...] = ()
