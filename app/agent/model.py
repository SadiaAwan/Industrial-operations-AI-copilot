"""Structured recommendation boundary with a deterministic local generator."""

from __future__ import annotations

from typing import Protocol

from pydantic import Field

from app.agent.state import AgentIntent
from app.domain.common import DomainModel, MachineId, Severity
from app.schemas.recommendations import (
    AgentRecommendation,
    Citation,
    Hypothesis,
    Observation,
    RecommendedCheck,
)
from app.schemas.tools import (
    DocumentSearchOutput,
    IncidentOutput,
    MaintenanceRecordOutput,
    SensorReadingOutput,
)


class RecommendationContext(DomainModel):
    machine_id: MachineId
    message: str = Field(min_length=1)
    intent: AgentIntent
    sensor_data: tuple[SensorReadingOutput, ...] = ()
    documents: tuple[DocumentSearchOutput, ...] = ()
    incidents: tuple[IncidentOutput, ...] = ()
    maintenance: tuple[MaintenanceRecordOutput, ...] = ()


class RecommendationGenerator(Protocol):
    async def generate(
        self,
        context: RecommendationContext,
    ) -> AgentRecommendation: ...


def _latest_sensor_values(
    readings: tuple[SensorReadingOutput, ...],
) -> dict[str, SensorReadingOutput]:
    latest: dict[str, SensorReadingOutput] = {}
    for reading in readings:
        previous = latest.get(reading.sensor_type)
        if previous is None or reading.recorded_at > previous.recorded_at:
            latest[reading.sensor_type] = reading
    return latest


def _sensor_observations(
    latest: dict[str, SensorReadingOutput],
) -> tuple[Observation, ...]:
    return tuple(
        Observation(
            statement=(
                f"{reading.sensor_type} is {reading.value:g} {reading.unit} "
                f"at {reading.recorded_at.isoformat()}"
            ),
            source_type="sensor",
            source_reference=reading.reading_id,
        )
        for reading in sorted(latest.values(), key=lambda item: item.sensor_type)
    )


def _document_observations(
    documents: tuple[DocumentSearchOutput, ...],
) -> tuple[Observation, ...]:
    return tuple(
        Observation(
            statement=document.content[:500],
            source_type="document",
            source_reference=document.citation.chunk_id,
        )
        for document in documents
    )


def _incident_observations(
    incidents: tuple[IncidentOutput, ...],
) -> tuple[Observation, ...]:
    return tuple(
        Observation(
            statement=incident.summary,
            source_type="incident",
            source_reference=incident.incident_id,
        )
        for incident in incidents[:5]
    )


def _maintenance_observations(
    maintenance: tuple[MaintenanceRecordOutput, ...],
) -> tuple[Observation, ...]:
    return tuple(
        Observation(
            statement=f"{record.maintenance_type}: {record.description}",
            source_type="maintenance",
            source_reference=record.record_id,
        )
        for record in maintenance[:3]
    )


def _value(
    latest: dict[str, SensorReadingOutput],
    sensor_type: str,
) -> float | None:
    reading = latest.get(sensor_type)
    return reading.value if reading else None


def _hypotheses(
    latest: dict[str, SensorReadingOutput],
    incidents: tuple[IncidentOutput, ...],
) -> tuple[Hypothesis, ...]:
    candidates: dict[str, Hypothesis] = {}
    vibration = _value(latest, "vibration_rms")
    temperature = _value(latest, "bearing_temperature")
    suction = _value(latest, "suction_pressure")
    flow = _value(latest, "flow_rate")
    current = _value(latest, "motor_current")

    if vibration is not None and temperature is not None:
        if vibration >= 6.0 and temperature >= 75.0:
            candidates["bearing degradation"] = Hypothesis(
                cause="bearing degradation",
                confidence=0.82,
                supporting_observation_refs=(
                    latest["vibration_rms"].reading_id,
                    latest["bearing_temperature"].reading_id,
                ),
            )
    if suction is not None and flow is not None:
        if suction <= 1.3 and flow <= 100.0:
            candidates["cavitation"] = Hypothesis(
                cause="cavitation",
                confidence=0.76,
                supporting_observation_refs=(
                    latest["suction_pressure"].reading_id,
                    latest["flow_rate"].reading_id,
                ),
            )
    if current is not None and current >= 30.0:
        candidates["motor overload"] = Hypothesis(
            cause="motor overload",
            confidence=0.74,
            supporting_observation_refs=(latest["motor_current"].reading_id,),
        )

    for incident in incidents:
        if incident.root_cause and incident.root_cause not in candidates:
            candidates[incident.root_cause] = Hypothesis(
                cause=incident.root_cause,
                confidence=0.55,
                supporting_observation_refs=(incident.incident_id,),
            )
    return tuple(
        sorted(candidates.values(), key=lambda item: (-item.confidence, item.cause))
    )[:5]


def _checks(hypotheses: tuple[Hypothesis, ...]) -> tuple[RecommendedCheck, ...]:
    checks = [
        RecommendedCheck(
            instruction=(
                "Follow the approved lockout/tagout procedure before physical "
                "inspection."
            ),
            rationale="Prevent exposure to rotating, electrical, and stored energy.",
            safety_critical=True,
        )
    ]
    by_cause = {
        "bearing degradation": (
            "Inspect the drive-end bearing and lubricant condition.",
            "Confirm whether the vibration and temperature trend has a bearing source.",
        ),
        "shaft misalignment": (
            "Verify shaft alignment, soft foot, and coupling condition.",
            "Misalignment can raise vibration and bearing load.",
        ),
        "cavitation": (
            "Check suction pressure, inlet restrictions, and liquid level.",
            "Confirm whether inadequate suction conditions explain the symptoms.",
        ),
        "motor overload": (
            "Compare motor current and speed with the approved operating envelope.",
            "Confirm whether process load or mechanical binding is present.",
        ),
    }
    for hypothesis in hypotheses[:3]:
        instruction, rationale = by_cause.get(
            hypothesis.cause,
            (
                f"Inspect evidence related to {hypothesis.cause}.",
                "Confirm the historical hypothesis before corrective work.",
            ),
        )
        checks.append(RecommendedCheck(instruction=instruction, rationale=rationale))
    return tuple(checks)


def _citations(
    documents: tuple[DocumentSearchOutput, ...],
) -> tuple[Citation, ...]:
    unique: dict[str, Citation] = {}
    for document in documents:
        source = document.citation
        unique.setdefault(
            source.chunk_id,
            Citation(
                document_id=source.document_id,
                title=source.title,
                revision=source.revision,
                section=source.section,
                chunk_id=source.chunk_id,
            ),
        )
    return tuple(unique.values())


class DeterministicRecommendationGenerator:
    """Offline generator used for tests; production injects a hosted model."""

    async def generate(
        self,
        context: RecommendationContext,
    ) -> AgentRecommendation:
        latest = _latest_sensor_values(context.sensor_data)
        observations = (
            _sensor_observations(latest)
            + _document_observations(context.documents)
            + _incident_observations(context.incidents)
            + _maintenance_observations(context.maintenance)
        )
        hypotheses = _hypotheses(latest, context.incidents)
        severity = Severity.NORMAL
        confidence = 0.45
        if hypotheses:
            confidence = hypotheses[0].confidence
            severity = Severity.HIGH if confidence >= 0.75 else Severity.MEDIUM

        sensor_summary = ", ".join(
            f"{item.sensor_type}={item.value:g} {item.unit}"
            for item in sorted(latest.values(), key=lambda value: value.sensor_type)
        )
        current_condition = sensor_summary or (
            "No current sensor readings were required for this request."
        )
        return AgentRecommendation(
            machine_id=context.machine_id,
            current_condition=current_condition,
            severity=severity,
            confidence=confidence,
            observations=observations,
            possible_causes=hypotheses,
            recommended_checks=_checks(hypotheses),
            safety_notice=(
                "This is diagnostic decision support, not an automatic control "
                "action. Follow approved site safety procedures."
            ),
            citations=_citations(context.documents),
        )
