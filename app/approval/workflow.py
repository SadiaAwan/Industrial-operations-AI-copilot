"""Human-in-the-loop approval state machine and execution gate."""

from __future__ import annotations

import json
import secrets
from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import Any, Protocol
from uuid import uuid4

from app.domain.approval import ApprovalAction, canonical_payload_hash
from app.domain.common import ApprovalStatus


class ApprovalWorkflowError(RuntimeError):
    pass


class ApprovalNotFound(ApprovalWorkflowError):
    pass


class ApprovalPayloadMismatch(ApprovalWorkflowError):
    pass


class ApprovalReplayBlocked(ApprovalWorkflowError):
    pass


class ApprovalExpired(ApprovalWorkflowError):
    pass


class ApprovalUserMismatch(ApprovalWorkflowError):
    pass


class ApprovalStore(Protocol):
    def get(
        self, action_id: str, *, for_update: bool = False
    ) -> ApprovalAction | None: ...

    def add(self, action: ApprovalAction) -> None: ...

    def save(self, action: ApprovalAction) -> None: ...


class ApprovedActionExecutor(Protocol):
    async def execute(
        self,
        *,
        idempotency_key: str,
        action_type: str,
        payload: Mapping[str, Any],
    ) -> None: ...


class ApprovalWorkflow:
    def __init__(self, store: ApprovalStore) -> None:
        self._store = store

    def propose(
        self,
        *,
        session_id: str,
        requested_by: str,
        action_type: str,
        payload: Mapping[str, Any],
        now: datetime,
        ttl: timedelta = timedelta(minutes=15),
    ) -> ApprovalAction:
        if ttl <= timedelta(0) or ttl > timedelta(hours=24):
            raise ValueError("approval ttl must be between 0 and 24 hours")
        payload_copy = json.loads(
            json.dumps(payload, allow_nan=False, ensure_ascii=True)
        )
        action = ApprovalAction(
            action_id=f"ACT-{uuid4().hex.upper()}",
            session_id=session_id,
            requested_by=requested_by,
            action_type=action_type,
            payload=payload_copy,
            payload_hash=canonical_payload_hash(payload_copy),
            status=ApprovalStatus.PENDING,
            created_at=now,
            expires_at=now + ttl,
        )
        self._store.add(action)
        return action

    def decide(
        self,
        *,
        action_id: str,
        user_id: str,
        payload_hash: str,
        approve: bool,
        now: datetime,
    ) -> ApprovalAction:
        action = self._required(action_id, for_update=True)
        if action.status != ApprovalStatus.PENDING:
            raise ApprovalReplayBlocked(
                f"approval action is already {action.status.value}"
            )
        if now > action.expires_at:
            expired = action.model_copy(update={"status": ApprovalStatus.EXPIRED})
            self._store.save(expired)
            return expired
        if not secrets.compare_digest(action.payload_hash, payload_hash):
            raise ApprovalPayloadMismatch("approval payload hash does not match")
        status = ApprovalStatus.APPROVED if approve else ApprovalStatus.REJECTED
        decided = action.model_copy(
            update={
                "status": status,
                "decided_at": now,
                "decided_by": user_id,
            }
        )
        validated = ApprovalAction.model_validate(decided.model_dump(mode="python"))
        self._store.save(validated)
        return validated

    async def execute(
        self,
        *,
        action_id: str,
        approved_by: str,
        payload: Mapping[str, Any],
        now: datetime,
        executor: ApprovedActionExecutor,
    ) -> ApprovalAction:
        action = self._required(action_id, for_update=True)
        if action.status != ApprovalStatus.APPROVED:
            raise ApprovalReplayBlocked(
                f"only approved actions may execute; status is {action.status.value}"
            )
        if now > action.expires_at:
            raise ApprovalExpired("approved action has expired")
        if action.decided_by != approved_by:
            raise ApprovalUserMismatch("approval is bound to a different user")
        supplied_hash = canonical_payload_hash(payload)
        if not secrets.compare_digest(action.payload_hash, supplied_hash):
            raise ApprovalPayloadMismatch(
                "executed payload differs from approved payload"
            )

        await executor.execute(
            idempotency_key=action.action_id,
            action_type=action.action_type,
            payload=action.payload,
        )
        executed = action.model_copy(
            update={
                "status": ApprovalStatus.EXECUTED,
                "executed_at": now,
            }
        )
        validated = ApprovalAction.model_validate(executed.model_dump(mode="python"))
        self._store.save(validated)
        return validated

    def _required(self, action_id: str, *, for_update: bool) -> ApprovalAction:
        action = self._store.get(action_id, for_update=for_update)
        if action is None:
            raise ApprovalNotFound(f"approval action not found: {action_id}")
        return action
