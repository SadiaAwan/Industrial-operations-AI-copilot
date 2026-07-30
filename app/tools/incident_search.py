"""Bounded read-only historical incident search tool."""

import asyncio
from collections.abc import Sequence
from typing import Protocol

from sqlalchemy.exc import OperationalError

from app.database.models import IncidentModel
from app.schemas.tools import IncidentOutput, IncidentSearchQuery, ToolResult
from app.tools.runtime import RetryableToolError, ToolExecutor, ToolNotFoundError
from app.tools.sensor_reader import MachineLookup


class IncidentReader(Protocol):
    def search(
        self,
        machine_id: str,
        *,
        query: str | None = None,
        limit: int = 20,
    ) -> Sequence[IncidentModel]: ...


class IncidentSearchTool:
    name = "search_incidents"

    def __init__(
        self,
        machines: MachineLookup,
        incidents: IncidentReader,
        *,
        executor: ToolExecutor | None = None,
    ) -> None:
        self._machines = machines
        self._incidents = incidents
        self._executor = executor or ToolExecutor()

    async def __call__(
        self, request: IncidentSearchQuery
    ) -> ToolResult[tuple[IncidentOutput, ...]]:
        def read() -> tuple[IncidentOutput, ...]:
            try:
                if self._machines.get(request.machine_id) is None:
                    raise ToolNotFoundError(f"unknown machine: {request.machine_id}")
                rows = self._incidents.search(
                    request.machine_id,
                    query=request.query,
                    limit=request.limit,
                )
            except OperationalError as exception:
                raise RetryableToolError from exception
            return tuple(
                IncidentOutput(
                    incident_id=row.incident_id,
                    machine_id=row.machine_id,
                    occurred_at=row.occurred_at,
                    severity=row.severity,
                    summary=row.summary,
                    root_cause=row.root_cause,
                    resolution=row.resolution,
                )
                for row in rows
            )

        return await self._executor.execute(self.name, lambda: asyncio.to_thread(read))
