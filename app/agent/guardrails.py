"""Deterministic safety, grounding, and prompt-injection guardrails."""

from __future__ import annotations

import re
from enum import StrEnum

from app.schemas.recommendations import AgentRecommendation
from app.schemas.tools import DocumentSearchOutput


class GuardrailCode(StrEnum):
    UNSAFE_REQUEST = "unsafe_request"
    PROMPT_INJECTION = "prompt_injection"
    FABRICATED_CITATION = "fabricated_citation"
    CONFLICTING_REVISION = "conflicting_revision"
    UNSUPPORTED_HYPOTHESIS = "unsupported_hypothesis"
    MISSING_SAFETY_NOTICE = "missing_safety_notice"


class GuardrailViolation(ValueError):
    def __init__(self, code: GuardrailCode, message: str) -> None:
        super().__init__(message)
        self.code = code


_UNSAFE_REQUESTS = (
    re.compile(
        r"\b(ignore|skip|bypass|disable)\b.{0,40}\b(lockout|tagout|loto)\b", re.I
    ),
    re.compile(
        r"\b(inspect|touch|open|repair)\b.{0,50}\b(running|energized|live)\b", re.I
    ),
    re.compile(r"\bwithout\b.{0,30}\b(approval|authorization|isolation)\b", re.I),
)
_PROMPT_INJECTIONS = (
    re.compile(
        r"\bignore (all |the )?(previous|prior|system|developer) instructions\b", re.I
    ),
    re.compile(r"\b(system|developer) (prompt|message|instructions)\b", re.I),
    re.compile(
        r"\b(call|execute|invoke)\b.{0,30}\b(tool|function|sql|command)\b", re.I
    ),
    re.compile(
        r"\b(reveal|expose|print)\b.{0,30}\b(secret|credential|token|prompt)\b", re.I
    ),
)


class GuardrailEngine:
    """Pure checks that cannot be weakened by model-generated text."""

    @staticmethod
    def validate_request(message: str) -> None:
        normalized = " ".join(message.split())
        if any(pattern.search(normalized) for pattern in _UNSAFE_REQUESTS):
            raise GuardrailViolation(
                GuardrailCode.UNSAFE_REQUEST,
                "request attempts to bypass an approved safety control",
            )

    @staticmethod
    def validate_documents(documents: tuple[DocumentSearchOutput, ...]) -> None:
        revisions: dict[str, str] = {}
        for document in documents:
            if any(pattern.search(document.content) for pattern in _PROMPT_INJECTIONS):
                raise GuardrailViolation(
                    GuardrailCode.PROMPT_INJECTION,
                    f"retrieved chunk rejected: {document.citation.chunk_id}",
                )
            previous = revisions.setdefault(
                document.citation.document_id, document.citation.revision
            )
            if previous != document.citation.revision:
                raise GuardrailViolation(
                    GuardrailCode.CONFLICTING_REVISION,
                    "conflicting revisions retrieved for "
                    f"{document.citation.document_id}",
                )

    def validate_recommendation(
        self,
        recommendation: AgentRecommendation,
        *,
        documents: tuple[DocumentSearchOutput, ...],
    ) -> None:
        self.validate_documents(documents)
        retrieved = {
            (
                item.citation.chunk_id,
                item.citation.document_id,
                item.citation.title,
                item.citation.revision,
                item.citation.section,
            )
            for item in documents
        }
        for citation in recommendation.citations:
            candidate = (
                citation.chunk_id,
                citation.document_id,
                citation.title,
                citation.revision,
                citation.section,
            )
            if candidate not in retrieved:
                raise GuardrailViolation(
                    GuardrailCode.FABRICATED_CITATION,
                    "citation does not resolve to retrieved evidence: "
                    f"{citation.chunk_id}",
                )

        observation_refs = {
            observation.source_reference for observation in recommendation.observations
        }
        for hypothesis in recommendation.possible_causes:
            if not hypothesis.supporting_observation_refs or not set(
                hypothesis.supporting_observation_refs
            ).issubset(observation_refs):
                raise GuardrailViolation(
                    GuardrailCode.UNSUPPORTED_HYPOTHESIS,
                    f"hypothesis lacks observed support: {hypothesis.cause}",
                )
            if hypothesis.confidence >= 1.0:
                raise GuardrailViolation(
                    GuardrailCode.UNSUPPORTED_HYPOTHESIS,
                    "hypotheses may not be presented as certain diagnoses",
                )

        if not recommendation.safety_notice.strip() or not any(
            check.safety_critical for check in recommendation.recommended_checks
        ):
            raise GuardrailViolation(
                GuardrailCode.MISSING_SAFETY_NOTICE,
                "recommendation must retain a safety notice and safety-critical check",
            )
