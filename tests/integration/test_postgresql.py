"""PostgreSQL integration tests for migration, seeding, and transactions."""

import os
from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.models import MachineModel, SensorReadingModel
from app.database.session import create_session_factory, transactional_session
from scripts.seed_database import seed_database


@pytest.fixture(scope="module")
def postgres_engine() -> Generator[Engine, None, None]:
    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL integration tests")
    database_name = database_url.rsplit("/", maxsplit=1)[-1].split("?", maxsplit=1)[0]
    if not database_name.endswith("_test"):
        pytest.fail("integration tests require a database name ending in '_test'")

    config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    os.environ["DATABASE_URL"] = database_url
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        yield engine
    finally:
        engine.dispose()
        command.downgrade(config, "base")


def test_migration_created_expected_tables(postgres_engine: Engine) -> None:
    from sqlalchemy import inspect

    tables = set(inspect(postgres_engine).get_table_names())
    assert {
        "machines",
        "sensor_readings",
        "maintenance_records",
        "incidents",
        "work_orders",
        "agent_sessions",
        "agent_feedback",
        "approval_actions",
    } <= tables


def test_seed_is_reproducible_and_idempotent(postgres_engine: Engine) -> None:
    factory = create_session_factory(postgres_engine)
    with transactional_session(factory) as session:
        expected = seed_database(session)
    with transactional_session(factory) as session:
        assert seed_database(session) == expected

    with Session(postgres_engine) as session:
        assert session.scalar(select(func.count()).select_from(MachineModel)) == 5
        assert (
            session.scalar(select(func.count()).select_from(SensorReadingModel)) == 420
        )


def test_foreign_key_constraint_blocks_unknown_machine(
    postgres_engine: Engine,
) -> None:
    with Session(postgres_engine) as session:
        session.add(
            SensorReadingModel(
                reading_id="SR-UNKNOWN",
                machine_id="P-999",
                sensor_type="motor_current",
                value=20.0,
                unit="A",
                recorded_at=datetime(2026, 7, 29, 10, 0, tzinfo=UTC),
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()


def test_transaction_rolls_back_on_error(postgres_engine: Engine) -> None:
    factory = create_session_factory(postgres_engine)
    with pytest.raises(RuntimeError, match="force rollback"):
        with transactional_session(factory) as session:
            session.add(
                MachineModel(
                    machine_id="P-999",
                    name="Rollback pump",
                    machine_type="centrifugal_pump",
                    status="active",
                )
            )
            session.flush()
            raise RuntimeError("force rollback")

    with Session(postgres_engine) as session:
        assert session.get(MachineModel, "P-999") is None
