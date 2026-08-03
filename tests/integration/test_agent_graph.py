"""End-to-end graph tests using deterministic phase-5 tool adapters."""

import asyncio
from datetime import UTC, date, datetime
from typing import Any, cast

from app.agent.graph import build_agent_graph
from app.agent.model import DeterministicRecommendationGenerator
from app.agent.nodes import AgentDependencies
from app.agent.state import AgentOutcome, AgentState, initial_agent_state
from app.database.models import (
    IncidentModel,
    MachineModel,
    MaintenanceRecordModel,
    SensorReadingModel,
)
from app.retrieval.chunking import DocumentChunk
from app.retrieval.embeddings import EmbeddedChunk
from app.retrieval.hybrid_search import SearchResult
from app.retrieval.metadata import ChunkMetadata, DocumentStatus
from app.tools.document_search import DocumentSearchTool
from app.tools.incident_search import IncidentSearchTool
from app.tools.maintenance_history import MaintenanceHistoryTool
from app.tools.sensor_reader import SensorDataTool
from app.tools.work_order import WorkOrderDraftTool

NOW = datetime(2026, 8, 2, 10, 0, tzinfo=UTC)


class FakeMachines:
    def __init__(self, *, exists: bool = True) -> None:
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
    def for_machine(
        self,
        machine_id: str,
        **arguments: Any,
    ) -> list[SensorReadingModel]:
        return [
            SensorReadingModel(
                reading_id="SR-VIB",
                machine_id=machine_id,
                sensor_type="vibration_rms",
                value=7.2,
                unit="mm/s RMS",
                recorded_at=NOW,
            ),
            SensorReadingModel(
                reading_id="SR-TEMP",
                machine_id=machine_id,
                sensor_type="bearing_temperature",
                value=82.0,
                unit="°C",
                recorded_at=NOW,
            ),
        ]


class FakeDocuments:
    async def search(
        self,
        query: str,
        **arguments: Any,
    ) -> tuple[SearchResult, ...]:
        metadata = ChunkMetadata(
            chunk_id="CH-7-3",
            document_id="pump_manual_v2",
            title="Pump manual",
            section="7.3 Bearing vibration",
            machine_type=arguments["filters"].machine_type,
            document_type="manual",
            revision="2.1",
            status=DocumentStatus.APPROVED,
            effective_date=date(2026, 1, 10),
            source_path="manuals/pump.md",
        )
        content = f"Evidence for {query}"
        return (
            SearchResult(
                embedded_chunk=EmbeddedChunk(
                    chunk=DocumentChunk(
                        metadata=metadata,
                        content=content,
                        character_count=len(content),
                    ),
                    vector=(1.0,),
                    embedding_model="test",
                ),
                score=0.9,
                keyword_rank=1,
                vector_rank=1,
            ),
        )


class FakeIncidents:
    def search(
        self,
        machine_id: str,
        **arguments: Any,
    ) -> list[IncidentModel]:
        return [
            IncidentModel(
                incident_id="INC-014",
                machine_id=machine_id,
                occurred_at=NOW,
                severity="high",
                summary="Similar vibration and temperature trend.",
                root_cause="bearing degradation",
                resolution="Bearing replaced.",
            )
        ]


class FakeMaintenance:
    def for_machine(
        self,
        machine_id: str,
        *,
        limit: int = 20,
    ) -> list[MaintenanceRecordModel]:
        return [
            MaintenanceRecordModel(
                record_id="MR-001",
                machine_id=machine_id,
                performed_at=NOW,
                maintenance_type="inspection",
                description=f"Latest of {limit} records.",
            )
        ]


def _dependencies(*, machine_exists: bool = True) -> AgentDependencies:
    machines = FakeMachines(exists=machine_exists)
    return AgentDependencies(
        sensor_tool=SensorDataTool(machines, FakeSensors()),
        document_tool=DocumentSearchTool(FakeDocuments()),
        incident_tool=IncidentSearchTool(machines, FakeIncidents()),
        maintenance_tool=MaintenanceHistoryTool(machines, FakeMaintenance()),
        work_order_tool=WorkOrderDraftTool(),
        recommendation_generator=DeterministicRecommendationGenerator(),
    )


def _invoke(
    message: str,
    *,
    machine_id: str | None = None,
    machine_exists: bool = True,
) -> AgentState:
    graph = build_agent_graph(_dependencies(machine_exists=machine_exists))
    state = initial_agent_state(
        message=message,
        session_id="SESSION-1",
        machine_id=machine_id,
        started_at=NOW,
    )
    return cast(AgentState, asyncio.run(graph.ainvoke(state)))


def test_diagnostic_graph_gathers_evidence_and_generates_response() -> None:
    result = _invoke("P-104 has high vibration and temperature. Diagnose it.")

    assert result["outcome"] == AgentOutcome.COMPLETED
    assert result["recommendation"] is not None
    assert result["recommendation"].possible_causes[0].cause == "bearing degradation"
    assert result["recommendation"].citations[0].chunk_id == "CH-7-3"
    assert tuple(call.tool_name for call in result["tool_calls"]) == (
        "read_sensor_data",
        "search_technical_documents",
        "search_incidents",
        "read_maintenance_history",
    )


def test_missing_machine_stops_before_tool_calls() -> None:
    result = _invoke("Why is the pump vibrating?")

    assert result["outcome"] == AgentOutcome.CLARIFICATION_REQUIRED
    assert result["clarification_required"] is True
    assert result["tool_calls"] == ()
    assert result["recommendation"] is None


def test_unknown_machine_returns_grounded_not_found_response() -> None:
    result = _invoke(
        "Show the latest readings for P-404",
        machine_exists=False,
    )

    assert result["outcome"] == AgentOutcome.MACHINE_NOT_FOUND
    assert result["recommendation"] is not None
    assert "not found" in result["recommendation"].current_condition
    assert len(result["tool_calls"]) == 1


def test_sensor_request_does_not_call_unnecessary_tools() -> None:
    result = _invoke("Show the latest sensor readings for P-104")

    assert result["outcome"] == AgentOutcome.COMPLETED
    assert tuple(call.tool_name for call in result["tool_calls"]) == (
        "read_sensor_data",
    )


def test_work_order_request_creates_draft_requiring_approval() -> None:
    result = _invoke("Create a work order draft for vibration on P-104")

    recommendation = result["recommendation"]
    assert recommendation is not None
    assert recommendation.requires_human_approval is True
    assert recommendation.proposed_action is not None
    assert recommendation.proposed_action.status == "pending_approval"
    assert result["proposed_action"] == recommendation.proposed_action
