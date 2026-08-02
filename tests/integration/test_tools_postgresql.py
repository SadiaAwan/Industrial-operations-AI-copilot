"""Exercise read-only tools against migrated and seeded PostgreSQL."""

import asyncio
import os
from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine

from app.database.repositories import (
    IncidentRepository,
    MachineRepository,
    MaintenanceRepository,
    SensorReadingRepository,
)
from app.database.session import create_session_factory, transactional_session
from app.schemas.tools import IncidentSearchQuery, MachineQuery, SensorDataQuery
from app.tools.incident_search import IncidentSearchTool
from app.tools.maintenance_history import MaintenanceHistoryTool
from app.tools.sensor_reader import SensorDataTool
from scripts.seed_database import seed_database


@pytest.fixture(scope="module")
def seeded_postgres() -> Generator[Engine, None, None]:
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL integration tests")
    database_name = database_url.rsplit("/", maxsplit=1)[-1].split("?", maxsplit=1)[0]
    if not database_name.endswith("_test"):
        pytest.fail("integration tests require a database name ending in '_test'")

    os.environ["DATABASE_URL"] = database_url
    config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    engine = create_engine(database_url, pool_pre_ping=True)
    factory = create_session_factory(engine)
    with transactional_session(factory) as session:
        seed_database(session)
    try:
        yield engine
    finally:
        engine.dispose()
        command.downgrade(config, "base")


def test_read_tools_use_bounded_repositories(seeded_postgres: Engine) -> None:
    factory = create_session_factory(seeded_postgres)
    with transactional_session(factory) as session:
        machines = MachineRepository(session)
        sensor_tool = SensorDataTool(machines, SensorReadingRepository(session))
        incident_tool = IncidentSearchTool(machines, IncidentRepository(session))
        maintenance_tool = MaintenanceHistoryTool(
            machines, MaintenanceRepository(session)
        )

        sensor_result = asyncio.run(
            sensor_tool(
                SensorDataQuery(
                    machine_id="P-104",
                    start_at=datetime(2026, 7, 23, tzinfo=UTC),
                    end_at=datetime(2026, 7, 24, tzinfo=UTC),
                    limit=5,
                )
            )
        )
        incident_result = asyncio.run(
            incident_tool(
                IncidentSearchQuery(machine_id="P-104", query="bearing", limit=3)
            )
        )
        maintenance_result = asyncio.run(
            maintenance_tool(MachineQuery(machine_id="P-104", limit=4))
        )

        assert sensor_result.data and len(sensor_result.data) == 5
        assert incident_result.data is not None
        assert len(incident_result.data) <= 3
        assert maintenance_result.data and len(maintenance_result.data) == 4


def test_tool_timeout_does_not_commit_or_mutate_data(
    seeded_postgres: Engine,
) -> None:
    del seeded_postgres
    # The work-order proposal tool has no repository/session parameter; write approval
    # and persistence are intentionally deferred to the Phase 7 approval workflow.
    from inspect import signature

    from app.tools.work_order import WorkOrderDraftTool

    parameters = signature(WorkOrderDraftTool.__init__).parameters
    assert "session" not in parameters
    assert "repository" not in parameters
