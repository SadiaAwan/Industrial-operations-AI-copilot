"""PostgreSQL integration tests for locked approval transitions and replay safety."""

import asyncio
import os
from collections.abc import Generator, Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, inspect

from app.approval.workflow import ApprovalReplayBlocked, ApprovalWorkflow
from app.database.models import AgentSessionModel
from app.database.repositories import ApprovalActionRepository
from app.database.session import create_session_factory, transactional_session
from app.domain.common import ApprovalStatus

NOW = datetime(2026, 8, 3, 10, 0, tzinfo=UTC)
PAYLOAD = {"machine_id": "P-104", "title": "Inspect drive-end bearing"}


class RecordingExecutor:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def execute(
        self,
        *,
        idempotency_key: str,
        action_type: str,
        payload: Mapping[str, Any],
    ) -> None:
        assert action_type == "create_work_order"
        assert payload == PAYLOAD
        self.calls.append(idempotency_key)


@pytest.fixture(scope="module")
def approval_database() -> Generator[Engine, None, None]:
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
    try:
        yield engine
    finally:
        engine.dispose()
        command.downgrade(config, "base")


def test_migration_adds_replay_safe_execution_column(
    approval_database: Engine,
) -> None:
    columns = {
        column["name"]
        for column in inspect(approval_database).get_columns("approval_actions")
    }
    assert "executed_at" in columns


def test_approved_payload_executes_once_and_persists_terminal_state(
    approval_database: Engine,
) -> None:
    factory = create_session_factory(approval_database)
    executor = RecordingExecutor()
    with transactional_session(factory) as session:
        session.add(
            AgentSessionModel(
                session_id="SESSION-APPROVAL-1",
                machine_id=None,
                status="waiting_for_approval",
                pending_action_ids=[],
                created_at=NOW,
                updated_at=NOW,
            )
        )
        session.flush()
        workflow = ApprovalWorkflow(ApprovalActionRepository(session))
        proposal = workflow.propose(
            session_id="SESSION-APPROVAL-1",
            requested_by="agent:SESSION-APPROVAL-1",
            action_type="create_work_order",
            payload=PAYLOAD,
            now=NOW,
        )
        approved = workflow.decide(
            action_id=proposal.action_id,
            user_id="operator-1",
            payload_hash=proposal.payload_hash,
            approve=True,
            now=NOW + timedelta(minutes=1),
        )
        executed = asyncio.run(
            workflow.execute(
                action_id=approved.action_id,
                approved_by="operator-1",
                payload=PAYLOAD,
                now=NOW + timedelta(minutes=2),
                executor=executor,
            )
        )
        action_id = executed.action_id

    with transactional_session(factory) as session:
        stored = ApprovalActionRepository(session).get(action_id, for_update=True)
        assert stored is not None
        assert stored.status == ApprovalStatus.EXECUTED
        assert stored.executed_at == NOW + timedelta(minutes=2)

        with pytest.raises(ApprovalReplayBlocked):
            asyncio.run(
                ApprovalWorkflow(ApprovalActionRepository(session)).execute(
                    action_id=action_id,
                    approved_by="operator-1",
                    payload=PAYLOAD,
                    now=NOW + timedelta(minutes=3),
                    executor=executor,
                )
            )

    assert executor.calls == [action_id]
