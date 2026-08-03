"""Bounded repositories; callers never receive unrestricted SQL access."""

from collections.abc import Sequence
from datetime import datetime
from typing import TypeVar

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.database.models import (
    ApprovalActionModel,
    IncidentModel,
    MachineModel,
    MaintenanceRecordModel,
    SensorReadingModel,
    WorkOrderModel,
)
from app.domain.approval import ApprovalAction

ModelT = TypeVar("ModelT")
MAX_RESULTS = 100


def _bounded(limit: int) -> int:
    if not 1 <= limit <= MAX_RESULTS:
        raise ValueError(f"limit must be between 1 and {MAX_RESULTS}")
    return limit


class Repository[ModelT]:
    def __init__(self, session: Session, model: type[ModelT]) -> None:
        self.session = session
        self.model = model

    def get(self, identifier: str) -> ModelT | None:
        return self.session.get(self.model, identifier)

    def add(self, item: ModelT) -> ModelT:
        self.session.add(item)
        return item

    def list(self, *, limit: int = 50) -> Sequence[ModelT]:
        statement: Select[tuple[ModelT]] = select(self.model).limit(_bounded(limit))
        return self.session.scalars(statement).all()


class MachineRepository(Repository[MachineModel]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, MachineModel)


class SensorReadingRepository(Repository[SensorReadingModel]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, SensorReadingModel)

    def for_machine(
        self,
        machine_id: str,
        *,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        limit: int = 100,
    ) -> Sequence[SensorReadingModel]:
        statement = select(SensorReadingModel).where(
            SensorReadingModel.machine_id == machine_id
        )
        if start_at is not None:
            statement = statement.where(SensorReadingModel.recorded_at >= start_at)
        if end_at is not None:
            statement = statement.where(SensorReadingModel.recorded_at <= end_at)
        statement = statement.order_by(SensorReadingModel.recorded_at.desc()).limit(
            _bounded(limit)
        )
        return self.session.scalars(statement).all()


class IncidentRepository(Repository[IncidentModel]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, IncidentModel)

    def search(
        self,
        machine_id: str,
        *,
        query: str | None = None,
        limit: int = 20,
    ) -> Sequence[IncidentModel]:
        statement = select(IncidentModel).where(IncidentModel.machine_id == machine_id)
        if query:
            escaped = (
                query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            )
            pattern = f"%{escaped}%"
            statement = statement.where(
                IncidentModel.summary.ilike(pattern, escape="\\")
            )
        statement = statement.order_by(IncidentModel.occurred_at.desc()).limit(
            _bounded(limit)
        )
        return self.session.scalars(statement).all()


class MaintenanceRepository(Repository[MaintenanceRecordModel]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, MaintenanceRecordModel)

    def for_machine(
        self, machine_id: str, *, limit: int = 20
    ) -> Sequence[MaintenanceRecordModel]:
        statement = (
            select(MaintenanceRecordModel)
            .where(MaintenanceRecordModel.machine_id == machine_id)
            .order_by(MaintenanceRecordModel.performed_at.desc())
            .limit(_bounded(limit))
        )
        return self.session.scalars(statement).all()


class WorkOrderRepository(Repository[WorkOrderModel]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, WorkOrderModel)


class ApprovalActionRepository:
    """Approval-only persistence with row locking for state transitions."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, action_id: str, *, for_update: bool = False) -> ApprovalAction | None:
        statement = select(ApprovalActionModel).where(
            ApprovalActionModel.action_id == action_id
        )
        if for_update:
            statement = statement.with_for_update()
        model = self.session.scalar(statement)
        return self._to_domain(model) if model is not None else None

    def add(self, action: ApprovalAction) -> None:
        self.session.add(self._to_model(action))

    def save(self, action: ApprovalAction) -> None:
        model = self.session.get(ApprovalActionModel, action.action_id)
        if model is None:
            raise LookupError(f"approval action not found: {action.action_id}")
        values = action.model_dump(mode="python")
        for field_name, value in values.items():
            setattr(model, field_name, value)

    @staticmethod
    def _to_domain(model: ApprovalActionModel) -> ApprovalAction:
        return ApprovalAction.model_validate(
            {
                "action_id": model.action_id,
                "session_id": model.session_id,
                "requested_by": model.requested_by,
                "action_type": model.action_type,
                "payload": model.payload,
                "payload_hash": model.payload_hash,
                "status": model.status,
                "created_at": model.created_at,
                "expires_at": model.expires_at,
                "decided_at": model.decided_at,
                "decided_by": model.decided_by,
                "executed_at": model.executed_at,
            }
        )

    @staticmethod
    def _to_model(action: ApprovalAction) -> ApprovalActionModel:
        return ApprovalActionModel(**action.model_dump(mode="python"))
