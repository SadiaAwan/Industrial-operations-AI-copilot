"""SQLAlchemy persistence models and relational constraints."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class MachineModel(TimestampMixin, Base):
    __tablename__ = "machines"
    __table_args__ = (
        CheckConstraint(
            "machine_id ~ '^[A-Z][A-Z0-9]*-[0-9]{3,6}$'",
            name="ck_machines_machine_id_format",
        ),
        CheckConstraint(
            "status IN ('active','inactive','maintenance','decommissioned')",
            name="ck_machines_status",
        ),
        Index("ix_machines_type_status", "machine_type", "status"),
    )

    machine_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    machine_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    location: Mapped[str | None] = mapped_column(String(255))

    sensor_readings: Mapped[list[SensorReadingModel]] = relationship(
        back_populates="machine", cascade="all, delete-orphan"
    )
    incidents: Mapped[list[IncidentModel]] = relationship(back_populates="machine")
    maintenance_records: Mapped[list[MaintenanceRecordModel]] = relationship(
        back_populates="machine"
    )


class SensorReadingModel(Base):
    __tablename__ = "sensor_readings"
    __table_args__ = (
        UniqueConstraint(
            "machine_id", "sensor_type", "recorded_at", name="uq_sensor_measurement"
        ),
        CheckConstraint("value = value", name="ck_sensor_value_not_nan"),
        Index(
            "ix_sensor_readings_machine_type_time",
            "machine_id",
            "sensor_type",
            "recorded_at",
        ),
    )

    reading_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    machine_id: Mapped[str] = mapped_column(
        ForeignKey("machines.machine_id", ondelete="CASCADE"), nullable=False
    )
    sensor_type: Mapped[str] = mapped_column(String(50), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    machine: Mapped[MachineModel] = relationship(back_populates="sensor_readings")


class MaintenanceRecordModel(TimestampMixin, Base):
    __tablename__ = "maintenance_records"
    __table_args__ = (
        Index("ix_maintenance_machine_performed", "machine_id", "performed_at"),
    )

    record_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    machine_id: Mapped[str] = mapped_column(
        ForeignKey("machines.machine_id", ondelete="RESTRICT"), nullable=False
    )
    performed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    maintenance_type: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    technician_id: Mapped[str | None] = mapped_column(String(64))

    machine: Mapped[MachineModel] = relationship(back_populates="maintenance_records")


class IncidentModel(TimestampMixin, Base):
    __tablename__ = "incidents"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('normal','low','medium','high','critical')",
            name="ck_incidents_severity",
        ),
        Index("ix_incidents_machine_occurred", "machine_id", "occurred_at"),
    )

    incident_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    machine_id: Mapped[str] = mapped_column(
        ForeignKey("machines.machine_id", ondelete="RESTRICT"), nullable=False
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    root_cause: Mapped[str | None] = mapped_column(Text)
    resolution: Mapped[str | None] = mapped_column(Text)

    machine: Mapped[MachineModel] = relationship(back_populates="incidents")


class WorkOrderModel(TimestampMixin, Base):
    __tablename__ = "work_orders"
    __table_args__ = (
        CheckConstraint(
            "priority IN ('normal','low','medium','high','critical')",
            name="ck_work_orders_priority",
        ),
        CheckConstraint(
            "status IN ('draft','pending_approval','approved','rejected','open',"
            "'in_progress','completed','cancelled')",
            name="ck_work_orders_status",
        ),
        Index("ix_work_orders_machine_status", "machine_id", "status"),
    )

    work_order_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    machine_id: Mapped[str] = mapped_column(
        ForeignKey("machines.machine_id", ondelete="RESTRICT"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    proposed_checks: Mapped[list[str]] = mapped_column(
        JSONB, default=list, nullable=False
    )


class AgentSessionModel(Base):
    __tablename__ = "agent_sessions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active','waiting_for_approval','completed','failed')",
            name="ck_agent_sessions_status",
        ),
        Index("ix_agent_sessions_machine_status", "machine_id", "status"),
    )

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    machine_id: Mapped[str | None] = mapped_column(
        ForeignKey("machines.machine_id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    pending_action_ids: Mapped[list[str]] = mapped_column(
        JSONB, default=list, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class AgentFeedbackModel(Base):
    __tablename__ = "agent_feedback"
    __table_args__ = (
        CheckConstraint(
            "rating IN ('helpful','not_helpful')", name="ck_agent_feedback_rating"
        ),
        Index("ix_agent_feedback_session_request", "session_id", "request_id"),
    )

    feedback_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("agent_sessions.session_id", ondelete="CASCADE"), nullable=False
    )
    request_id: Mapped[str] = mapped_column(String(64), nullable=False)
    rating: Mapped[str] = mapped_column(String(20), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    agent_version: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class ApprovalActionModel(Base):
    __tablename__ = "approval_actions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','approved','rejected','expired')",
            name="ck_approval_actions_status",
        ),
        CheckConstraint("expires_at > created_at", name="ck_approval_expiry"),
        CheckConstraint(
            "(status IN ('approved','rejected') AND decided_at IS NOT NULL AND "
            "decided_by IS NOT NULL) OR (status IN ('pending','expired') AND "
            "decided_at IS NULL AND decided_by IS NULL)",
            name="ck_approval_decision_metadata",
        ),
        Index("ix_approval_session_status", "session_id", "status"),
    )

    action_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("agent_sessions.session_id", ondelete="CASCADE"), nullable=False
    )
    requested_by: Mapped[str] = mapped_column(String(100), nullable=False)
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decided_by: Mapped[str | None] = mapped_column(String(100))
