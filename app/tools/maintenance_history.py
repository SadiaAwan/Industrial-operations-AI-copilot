"""Bounded read-only maintenance-history tool."""

import asyncio
from collections.abc import Sequence
from typing import Protocol

from sqlalchemy.exc import OperationalError

from app.database.models import MaintenanceRecordModel
from app.schemas.tools import (
    MachineQuery,
    MaintenanceRecordOutput,
    ToolResult,
)
from app.tools.runtime import RetryableToolError, ToolExecutor, ToolNotFoundError
from app.tools.sensor_reader import MachineLookup


class MaintenanceReader(Protocol):
    def for_machine(
        self, machine_id: str, *, limit: int = 20
    ) -> Sequence[MaintenanceRecordModel]: ...


class MaintenanceHistoryTool:
    name = "read_maintenance_history"

    def __init__(
        self,
        machines: MachineLookup,
        maintenance: MaintenanceReader,
        *,
        executor: ToolExecutor | None = None,
    ) -> None:
        self._machines = machines
        self._maintenance = maintenance
        self._executor = executor or ToolExecutor()

    async def __call__(
        self, request: MachineQuery
    ) -> ToolResult[tuple[MaintenanceRecordOutput, ...]]:
        def read() -> tuple[MaintenanceRecordOutput, ...]:
            try:
                if self._machines.get(request.machine_id) is None:
                    raise ToolNotFoundError(f"unknown machine: {request.machine_id}")
                rows = self._maintenance.for_machine(
                    request.machine_id, limit=request.limit
                )
            except OperationalError as exception:
                raise RetryableToolError from exception
            return tuple(
                MaintenanceRecordOutput(
                    record_id=row.record_id,
                    machine_id=row.machine_id,
                    performed_at=row.performed_at,
                    maintenance_type=row.maintenance_type,
                    description=row.description,
                    technician_id=row.technician_id,
                )
                for row in rows
            )

        return await self._executor.execute(self.name, lambda: asyncio.to_thread(read))
