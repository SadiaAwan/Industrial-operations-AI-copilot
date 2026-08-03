"""Negative and positive tests for the human approval state machine."""

import asyncio
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from app.approval.workflow import (
    ApprovalPayloadMismatch,
    ApprovalReplayBlocked,
    ApprovalUserMismatch,
    ApprovalWorkflow,
)
from app.domain.approval import ApprovalAction
from app.domain.common import ApprovalStatus

NOW = datetime(2026, 8, 3, 10, 0, tzinfo=UTC)
PAYLOAD = {"machine_id": "P-104", "title": "Inspect bearing"}


class MemoryApprovalStore:
    def __init__(self) -> None:
        self.actions: dict[str, ApprovalAction] = {}

    def get(self, action_id: str, *, for_update: bool = False) -> ApprovalAction | None:
        del for_update
        return self.actions.get(action_id)

    def add(self, action: ApprovalAction) -> None:
        self.actions[action.action_id] = action

    def save(self, action: ApprovalAction) -> None:
        self.actions[action.action_id] = action


class RecordingExecutor:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, Mapping[str, Any]]] = []

    async def execute(
        self,
        *,
        idempotency_key: str,
        action_type: str,
        payload: Mapping[str, Any],
    ) -> None:
        self.calls.append((idempotency_key, action_type, payload))


def _proposal(
    workflow: ApprovalWorkflow, *, ttl: timedelta = timedelta(minutes=15)
) -> ApprovalAction:
    return workflow.propose(
        session_id="SESSION-1",
        requested_by="agent:SESSION-1",
        action_type="create_work_order",
        payload=PAYLOAD,
        now=NOW,
        ttl=ttl,
    )


def _approve(workflow: ApprovalWorkflow, action: ApprovalAction) -> ApprovalAction:
    return workflow.decide(
        action_id=action.action_id,
        user_id="operator-1",
        payload_hash=action.payload_hash,
        approve=True,
        now=NOW + timedelta(minutes=1),
    )


def test_proposal_is_pending_and_bound_to_exact_payload() -> None:
    store = MemoryApprovalStore()
    action = _proposal(ApprovalWorkflow(store))

    assert action.status == ApprovalStatus.PENDING
    assert action.payload == PAYLOAD
    assert store.actions[action.action_id] == action


def test_changed_payload_cannot_be_approved() -> None:
    workflow = ApprovalWorkflow(MemoryApprovalStore())
    action = _proposal(workflow)

    with pytest.raises(ApprovalPayloadMismatch):
        workflow.decide(
            action_id=action.action_id,
            user_id="operator-1",
            payload_hash="0" * 64,
            approve=True,
            now=NOW + timedelta(minutes=1),
        )


def test_expired_proposal_cannot_be_approved() -> None:
    workflow = ApprovalWorkflow(MemoryApprovalStore())
    action = _proposal(workflow, ttl=timedelta(seconds=1))

    expired = workflow.decide(
        action_id=action.action_id,
        user_id="operator-1",
        payload_hash=action.payload_hash,
        approve=True,
        now=NOW + timedelta(seconds=2),
    )
    assert expired.status == ApprovalStatus.EXPIRED


def test_rejected_action_cannot_execute() -> None:
    workflow = ApprovalWorkflow(MemoryApprovalStore())
    action = _proposal(workflow)
    rejected = workflow.decide(
        action_id=action.action_id,
        user_id="operator-1",
        payload_hash=action.payload_hash,
        approve=False,
        now=NOW + timedelta(minutes=1),
    )

    with pytest.raises(ApprovalReplayBlocked):
        asyncio.run(
            workflow.execute(
                action_id=rejected.action_id,
                approved_by="operator-1",
                payload=PAYLOAD,
                now=NOW + timedelta(minutes=2),
                executor=RecordingExecutor(),
            )
        )


def test_approval_is_bound_to_deciding_user() -> None:
    workflow = ApprovalWorkflow(MemoryApprovalStore())
    approved = _approve(workflow, _proposal(workflow))

    with pytest.raises(ApprovalUserMismatch):
        asyncio.run(
            workflow.execute(
                action_id=approved.action_id,
                approved_by="different-operator",
                payload=PAYLOAD,
                now=NOW + timedelta(minutes=2),
                executor=RecordingExecutor(),
            )
        )


def test_modified_payload_cannot_execute_after_approval() -> None:
    workflow = ApprovalWorkflow(MemoryApprovalStore())
    approved = _approve(workflow, _proposal(workflow))

    with pytest.raises(ApprovalPayloadMismatch):
        asyncio.run(
            workflow.execute(
                action_id=approved.action_id,
                approved_by="operator-1",
                payload={**PAYLOAD, "priority": "critical"},
                now=NOW + timedelta(minutes=2),
                executor=RecordingExecutor(),
            )
        )


def test_approved_action_executes_once_with_idempotency_key() -> None:
    workflow = ApprovalWorkflow(MemoryApprovalStore())
    approved = _approve(workflow, _proposal(workflow))
    executor = RecordingExecutor()

    executed = asyncio.run(
        workflow.execute(
            action_id=approved.action_id,
            approved_by="operator-1",
            payload=PAYLOAD,
            now=NOW + timedelta(minutes=2),
            executor=executor,
        )
    )

    assert executed.status == ApprovalStatus.EXECUTED
    assert executor.calls[0][0] == approved.action_id
    with pytest.raises(ApprovalReplayBlocked):
        asyncio.run(
            workflow.execute(
                action_id=approved.action_id,
                approved_by="operator-1",
                payload=PAYLOAD,
                now=NOW + timedelta(minutes=3),
                executor=executor,
            )
        )
    assert len(executor.calls) == 1
