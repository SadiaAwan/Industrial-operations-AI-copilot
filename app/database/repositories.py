"""Bounded repositories; callers never receive unrestricted SQL access."""

from collections.abc import Sequence
from datetime import datetime
from typing import TypeVar

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.database.models import (
    IncidentModel,
    MachineModel,
    MaintenanceRecordModel,
    SensorReadingModel,
    WorkOrderModel,
)

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


class MaintenanceRepository(Repository[MaintenanceRecordModel]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, MaintenanceRecordModel)


class WorkOrderRepository(Repository[WorkOrderModel]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, WorkOrderModel)
