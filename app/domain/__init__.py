"""Stable domain contracts shared by persistence, tools, API, and agent layers."""

from app.domain.approval import ApprovalAction
from app.domain.common import (
    ApprovalStatus,
    FeedbackRating,
    MachineStatus,
    SessionStatus,
    Severity,
    WorkOrderStatus,
)
from app.domain.feedback import AgentFeedback
from app.domain.incident import Incident
from app.domain.machine import Machine
from app.domain.maintenance_record import MaintenanceRecord
from app.domain.sensor_reading import SensorReading, SensorType, SensorUnit
from app.domain.session import AgentSession
from app.domain.work_order import WorkOrder, WorkOrderDraft

__all__ = [
    "AgentFeedback",
    "AgentSession",
    "ApprovalAction",
    "ApprovalStatus",
    "FeedbackRating",
    "Incident",
    "Machine",
    "MachineStatus",
    "MaintenanceRecord",
    "SensorReading",
    "SensorType",
    "SensorUnit",
    "SessionStatus",
    "Severity",
    "WorkOrder",
    "WorkOrderDraft",
    "WorkOrderStatus",
]
