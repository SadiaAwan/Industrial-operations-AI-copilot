"""Unit tests for validation, safety boundaries, retries, and tracing."""

import asyncio
from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest
from pydantic import ValidationError

from app.database.models import (
    IncidentModel,
    MachineModel,
    MaintenanceRecordModel,
    SensorReadingModel,
)
from app.observability.tracing import InMemoryToolTracer
from app.retrieval.chunking import DocumentChunk
from app.retrieval.embeddings import EmbeddedChunk
from app.retrieval.hybrid_search import SearchResult
from app.retrieval.metadata import ChunkMetadata, DocumentStatus
from app.schemas.tools import (
    DocumentSearchQuery,
    IncidentSearchQuery,
    MachineQuery,
    SensorDataQuery,
    ToolErrorCode,
    WorkOrderDraftRequest,
)
from app.tools.document_search import DocumentSearchTool
from app.tools.incident_search import IncidentSearchTool
from app.tools.maintenance_history import MaintenanceHistoryTool
from app.tools.registry import ToolRegistry
from app.tools.runtime import RetryableToolError, ToolExecutor, ToolPolicy
from app.tools.sensor_reader import SensorDataTool
from app.tools.work_order import WorkOrderDraftTool

NOW = datetime(2026, 7, 31, 10, 0, tzinfo=UTC)


class FakeMachines:
    def __init__(self, exists: bool = True) -> None:
        self.exists = exists

    def get(self, identifier: str) -> MachineModel | None:
        if not self.exists:
            return None
        return MachineModel(
            machine_id=identifier,
            name="Pump",
            machine_type="centrifugal_pump",
            status="active",
        )


class FakeSensors:
    def __init__(self) -> None:
        self.arguments: dict[str, Any] = {}

    def for_machine(
        self, machine_id: str, **arguments: Any
    ) -> list[SensorReadingModel]:
        self.arguments = {"machine_id": machine_id, **arguments}
        return [
            SensorReadingModel(
                reading_id="SR-1",
                machine_id=machine_id,
                sensor_type="vibration_rms",
                value=7.2,
                unit="mm/s RMS",
                recorded_at=NOW,
            )
        ]


class FakeIncidents:
    def search(self, machine_id: str, **arguments: Any) -> list[IncidentModel]:
        return [
            IncidentModel(
                incident_id="INC-1",
                machine_id=machine_id,
                occurred_at=NOW,
                severity="high",
                summary=f"Matched {arguments.get('query')}",
            )
        ]


class FakeMaintenance:
    def for_machine(
        self, machine_id: str, *, limit: int = 20
    ) -> list[MaintenanceRecordModel]:
        return [
            MaintenanceRecordModel(
                record_id="MR-1",
                machine_id=machine_id,
                performed_at=NOW,
                maintenance_type="inspection",
                description=f"Limited to {limit}",
            )
        ]


class FakeDocuments:
    async def search(self, query: str, **arguments: Any) -> tuple[SearchResult, ...]:
        metadata = ChunkMetadata(
            chunk_id="CH-1",
            document_id="manual-v2",
            title="Pump manual",
            section="7.3 Bearings",
            machine_type=arguments["filters"].machine_type,
            document_type="manual",
            revision="2.0",
            status=DocumentStatus.APPROVED,
            effective_date=date(2026, 1, 1),
            source_path="manuals/pump.md",
        )
        chunk = DocumentChunk(
            metadata=metadata,
            content=f"Evidence for {query}",
            character_count=len(f"Evidence for {query}"),
        )
        return (
            SearchResult(
                embedded_chunk=EmbeddedChunk(
                    chunk=chunk, vector=(1.0,), embedding_model="test"
                ),
                score=0.9,
                keyword_rank=1,
                vector_rank=1,
            ),
        )


def test_sensor_tool_passes_validated_bounded_arguments() -> None:
    readings = FakeSensors()
    tool = SensorDataTool(FakeMachines(), readings)
    request = SensorDataQuery(
        machine_id="P-104",
        start_at=NOW - timedelta(hours=1),
        end_at=NOW,
        limit=7,
    )
    result = asyncio.run(tool(request))

    assert result.error is None
    assert result.data and result.data[0].unit == "mm/s RMS"
    assert readings.arguments["limit"] == 7
    assert readings.arguments["machine_id"] == "P-104"


def test_unknown_machine_returns_stable_not_found_error() -> None:
    request = MachineQuery(machine_id="P-404", limit=5)
    result = asyncio.run(
        MaintenanceHistoryTool(FakeMachines(False), FakeMaintenance())(request)
    )

    assert result.data is None
    assert result.error and result.error.code == ToolErrorCode.NOT_FOUND
    assert result.error.retryable is False


def test_empty_results_are_successful() -> None:
    class EmptyIncidents(FakeIncidents):
        def search(self, machine_id: str, **arguments: Any) -> list[IncidentModel]:
            return []

    result = asyncio.run(
        IncidentSearchTool(FakeMachines(), EmptyIncidents())(
            IncidentSearchQuery(machine_id="P-104", query="cavitation")
        )
    )
    assert result.data == ()
    assert result.error is None


def test_document_tool_returns_resolvable_citation() -> None:
    result = asyncio.run(
        DocumentSearchTool(FakeDocuments())(
            DocumentSearchQuery(
                query="bearing vibration", machine_type="centrifugal_pump", limit=3
            )
        )
    )
    assert result.data
    assert result.data[0].citation.reference == "manual-v2#7.3 Bearings"


def test_work_order_tool_is_idempotent_and_has_no_write_dependency() -> None:
    tool = WorkOrderDraftTool()
    request = WorkOrderDraftRequest(
        machine_id="P-104",
        title="Inspect bearing",
        description="Inspect drive-end bearing after lockout/tagout.",
        priority="high",
        proposed_checks=("Verify isolation", "Inspect bearing"),
    )
    first = asyncio.run(tool(request))
    second = asyncio.run(tool(request))

    assert first == second
    assert first.data and first.data.status == "pending_approval"


def test_timeout_retries_are_bounded_and_traced_without_payload() -> None:
    tracer = InMemoryToolTracer()
    executor = ToolExecutor(
        policy=ToolPolicy(timeout_seconds=0.001, max_attempts=2), tracer=tracer
    )

    async def slow() -> str:
        await asyncio.sleep(0.05)
        return "secret payload"

    result = asyncio.run(executor.execute("slow_tool", slow))

    assert result.error and result.error.code == ToolErrorCode.TIMEOUT
    assert tracer.traces[0].attempt_count == 2
    assert "secret" not in repr(tracer.traces[0])


def test_retryable_dependency_error_succeeds_on_second_attempt() -> None:
    attempts = 0
    executor = ToolExecutor(policy=ToolPolicy(max_attempts=2))

    async def flaky() -> str:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RetryableToolError
        return "ok"

    result = asyncio.run(executor.execute("flaky", flaky))
    assert result.data == "ok"
    assert attempts == 2


def test_registry_blocks_non_allowlisted_tools() -> None:
    registry = ToolRegistry({"read_sensor_data": lambda: None})
    assert registry.names == ("read_sensor_data",)
    with pytest.raises(LookupError, match="not allowed"):
        registry.get("execute_sql")


@pytest.mark.parametrize(
    "payload",
    [
        {"machine_id": "P-104", "start_at": NOW, "end_at": NOW, "limit": 101},
        {
            "machine_id": "P-104",
            "start_at": NOW,
            "end_at": NOW - timedelta(seconds=1),
        },
    ],
)
def test_invalid_sensor_arguments_are_rejected(payload: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        SensorDataQuery.model_validate(payload)
