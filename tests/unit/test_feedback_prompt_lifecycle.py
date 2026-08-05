from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.agent.prompt_lifecycle import (
    PromptRegistry,
    PromptVersion,
    evaluate_prompt_candidate,
)
from app.domain.common import FeedbackRating
from app.domain.feedback import AgentFeedback
from app.evaluation import load_evaluation_dataset, run_evaluation
from app.evaluation.feedback_cases import FeedbackCaseInput, curate_feedback_cases
from app.evaluation.gates import ReleaseGateError
from app.schemas.feedback import FeedbackCreate

NOW = datetime(2026, 8, 5, 12, 0, tzinfo=UTC)
PROMPT_DIGEST = "3b73b8f5d12675bca6fd46f290020aedad45cebf3356d657fec560c9c9228194"
MANIFEST = Path("app/agent/prompts/manifest.json")
REFERENCE = Path("evaluation/expected_outputs/phase11_reference_results.json")


def _feedback_case() -> FeedbackCaseInput:
    return FeedbackCaseInput(
        feedback_id="FEEDBACK-1",
        session_id="SESSION-1",
        trace_id="TRACE-1",
        rating=FeedbackRating.NOT_HELPFUL,
        agent_version="phase-12",
        prompt_version="diagnostics-v1",
        prompt_sha256=PROMPT_DIGEST,
        reviewed=True,
        include_in_evaluation=True,
        case_id="FEEDBACK-EVAL-1",
        expected_outcome="completed",
        expected_causes=("bearing degradation",),
        expected_tools=("read_sensor_data",),
    )


def test_feedback_is_traceable_and_free_text_is_sanitized() -> None:
    payload = FeedbackCreate(
        session_id="SESSION-1",
        request_id="REQUEST-1",
        rating=FeedbackRating.NOT_HELPFUL,
        comment="Contact Ada@example.com or +46 70 123 45 67; token=abc123",
    )
    feedback = AgentFeedback(
        feedback_id="FEEDBACK-1",
        trace_id="TRACE-1",
        agent_version="phase-12",
        prompt_version="diagnostics-v1",
        prompt_sha256=PROMPT_DIGEST,
        model_version="model-v1",
        created_at=NOW,
        **payload.model_dump(),
    )

    assert feedback.trace_id == "TRACE-1"
    assert feedback.prompt_sha256 == PROMPT_DIGEST
    assert "Ada@example.com" not in (feedback.comment or "")
    assert "abc123" not in (feedback.comment or "")
    assert "[REDACTED_EMAIL]" in (feedback.comment or "")


def test_prompt_registry_verifies_content_digest() -> None:
    registry = PromptRegistry(MANIFEST)

    prompt = registry.get("diagnostics", "diagnostics-v1")

    assert prompt.status == "active"
    assert "Evidence rules" in registry.content(prompt.prompt_id, prompt.version)
    assert len(registry.fingerprint()) == 64


def test_feedback_curation_excludes_session_and_free_text() -> None:
    dataset = curate_feedback_cases(
        (_feedback_case(),),
        dataset_id="feedback-regressions",
        dataset_version="1.0.0",
        generated_at=NOW,
    )

    serialized = dataset.model_dump_json()
    assert dataset.cases[0].source_trace_id == "TRACE-1"
    assert "SESSION-1" not in serialized
    assert "comment" not in serialized


def test_unreviewed_feedback_cannot_enter_eval_dataset() -> None:
    payload = _feedback_case().model_dump()
    payload["reviewed"] = False
    with pytest.raises(ValueError, match="human review"):
        FeedbackCaseInput.model_validate(payload)


def test_new_prompt_version_must_pass_eval_regression_gate() -> None:
    dataset, fingerprint = load_evaluation_dataset(REFERENCE)
    baseline_report = run_evaluation(dataset, fingerprint, generated_at=NOW)
    candidate_report = baseline_report.model_copy(
        update={
            "metric_averages": {
                **baseline_report.metric_averages,
                "groundedness": 0.0,
            }
        }
    )
    baseline = PromptVersion(
        prompt_id="diagnostics",
        version="diagnostics-v1",
        file="diagnostics_v1.md",
        sha256=PROMPT_DIGEST,
        status="active",
    )
    candidate = baseline.model_copy(
        update={"version": "diagnostics-v2", "status": "candidate"}
    )

    with pytest.raises(ReleaseGateError):
        evaluate_prompt_candidate(
            baseline=baseline,
            candidate=candidate,
            baseline_report=baseline_report,
            candidate_report=candidate_report,
        )
