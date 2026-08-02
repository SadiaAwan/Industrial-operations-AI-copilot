"""Deterministic intent classification and graph routing rules."""

from __future__ import annotations

import re
from collections.abc import Mapping

from app.agent.state import AgentIntent, AgentOutcome, AgentState
from app.domain.common import MACHINE_ID_PATTERN

_MACHINE_PATTERN = MACHINE_ID_PATTERN.pattern[1:-1]
_MACHINE_IN_TEXT = re.compile(rf"(?<![A-Z0-9])({_MACHINE_PATTERN})(?![A-Z0-9])")

_INTENT_TERMS: Mapping[AgentIntent, tuple[str, ...]] = {
    AgentIntent.WORK_ORDER_DRAFT: (
        "work order",
        "work-order",
        "arbetsorder",
        "create a draft",
        "prepare a draft",
    ),
    AgentIntent.SAFETY_PROCEDURE: (
        "safety",
        "lockout",
        "tagout",
        "safe",
        "säker",
    ),
    AgentIntent.MAINTENANCE_HISTORY: (
        "maintenance history",
        "maintained",
        "serviced",
        "service history",
        "underhåll",
    ),
    AgentIntent.INCIDENT_SEARCH: (
        "incident",
        "historical failure",
        "similar failure",
        "tidigare fel",
    ),
    AgentIntent.SENSOR_STATUS: (
        "sensor",
        "latest reading",
        "current reading",
        "show readings",
        "show the latest",
        "sensor status",
    ),
}


def extract_machine_id(message: str) -> str | None:
    match = _MACHINE_IN_TEXT.search(message.upper())
    return match.group(1) if match else None


def classify_intent(message: str) -> AgentIntent:
    normalized = " ".join(message.casefold().split())
    for intent, terms in _INTENT_TERMS.items():
        if any(term in normalized for term in terms):
            return intent
    return AgentIntent.DIAGNOSTIC


def route_after_validation(state: AgentState) -> str:
    if state["step_count"] >= state["max_steps"]:
        return "loop_limit"
    if state["clarification_required"]:
        return "clarification"
    return "classify"


def route_from_intent(state: AgentState) -> str:
    routes = {
        AgentIntent.DIAGNOSTIC: "sensor",
        AgentIntent.SENSOR_STATUS: "sensor",
        AgentIntent.INCIDENT_SEARCH: "incidents",
        AgentIntent.MAINTENANCE_HISTORY: "maintenance",
        AgentIntent.SAFETY_PROCEDURE: "documents",
        AgentIntent.WORK_ORDER_DRAFT: "sensor",
    }
    return routes[state["intent"]]


def route_after_sensor(state: AgentState) -> str:
    if state["outcome"] == AgentOutcome.MACHINE_NOT_FOUND:
        return "finalize"
    if state["intent"] == AgentIntent.SENSOR_STATUS:
        return "assess"
    return "documents"


def route_after_documents(state: AgentState) -> str:
    if state["intent"] == AgentIntent.SAFETY_PROCEDURE:
        return "assess"
    return "incidents"


def route_after_incidents(state: AgentState) -> str:
    if state["intent"] == AgentIntent.INCIDENT_SEARCH:
        return "assess"
    return "maintenance"


def route_after_assessment(state: AgentState) -> str:
    if state["evidence_sufficient"]:
        return "generate"
    return "finalize"


def route_after_generation(state: AgentState) -> str:
    if state["intent"] == AgentIntent.WORK_ORDER_DRAFT:
        return "draft"
    return "finalize"
