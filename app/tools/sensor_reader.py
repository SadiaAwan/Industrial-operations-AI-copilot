"""Bounded read-only sensor-data tool."""

import asyncio
from collections.abc import Sequence
from typing import Protocol

from sqlalchemy.exc import OperationalError

from app.database.models import MachineModel, SensorReadingModel
from app.schemas.tools import SensorDataQuery, SensorReadingOutput, ToolResult
from app.tools.runtime import (
    RetryableToolError,
    ToolExecutor,
    ToolNotFoundError,
)


class MachineLookup(Protocol):
    def get(self, identifier: str) -> MachineModel | None: ...


class SensorReader(Protocol):
    def for_machine(
        self,
        machine_id: str,
        *,
        start_at: object | None = None,
        end_at: object | None = None,
        limit: int = 100,
    ) -> Sequence[SensorReadingModel]: ...


class SensorDataTool:
    name = "read_sensor_data"

    def __init__(
        self,
        machines: MachineLookup,
        readings: SensorReader,
        *,
        executor: ToolExecutor | None = None,
    ) -> None:
        self._machines = machines
        self._readings = readings
        self._executor = executor or ToolExecutor()

    async def __call__(
        self, request: SensorDataQuery
    ) -> ToolResult[tuple[SensorReadingOutput, ...]]:
        def read() -> tuple[SensorReadingOutput, ...]:
            try:
                if self._machines.get(request.machine_id) is None:
                    raise ToolNotFoundError(f"unknown machine: {request.machine_id}")
                rows = self._readings.for_machine(
                    request.machine_id,
                    start_at=request.start_at,
                    end_at=request.end_at,
                    limit=request.limit,
                )
            except OperationalError as exception:
                raise RetryableToolError from exception
            return tuple(
                SensorReadingOutput(
                    reading_id=row.reading_id,
                    machine_id=row.machine_id,
                    sensor_type=row.sensor_type,
                    value=row.value,
                    unit=row.unit,
                    recorded_at=row.recorded_at,
                )
                for row in rows
            )

        return await self._executor.execute(self.name, lambda: asyncio.to_thread(read))
