"""Positive and negative contracts for every Phase 11 scorer."""

from evaluation.scorers import (
    ClaimEvidence,
    EvaluationResult,
    score_citation_correctness,
    score_cost_efficiency,
    score_groundedness,
    score_latency,
    score_task_completion,
    score_tool_behavior,
    score_tool_selection,
)


def result(**updates: object) -> EvaluationResult:
    values: dict[str, object] = {
        "case_id": "CASE-1",
        "expected_outcome": "completed",
        "actual_outcome": "completed",
        "expected_causes": ("bearing degradation",),
        "actual_causes": ("bearing degradation",),
        "expected_citations": ("manual#7.3",),
        "actual_citations": ("manual#7.3",),
        "expected_tools": ("read_sensor_data",),
        "forbidden_tools": ("create_work_order_draft",),
        "actual_tools": ("read_sensor_data",),
        "claims": (
            ClaimEvidence(
                claim="Vibration is elevated",
                supported=True,
                source_references=("sensor:R-1",),
            ),
        ),
        "latency_ms": 500,
        "estimated_cost_usd": 0.01,
    }
    values.update(updates)
    return EvaluationResult.model_validate(values)


def test_compliant_result_passes_all_scorers() -> None:
    candidate = result()
    scores = (
        score_groundedness(candidate),
        score_citation_correctness(candidate),
        score_task_completion(candidate),
        score_tool_selection(candidate),
        score_tool_behavior(candidate),
        score_latency(candidate),
        score_cost_efficiency(candidate),
    )

    assert all(score.passed for score in scores)
    assert all(score.value == 1 for score in scores)


def test_unsupported_claim_fails_groundedness() -> None:
    score = score_groundedness(
        result(
            claims=(
                ClaimEvidence(
                    claim="The bearing has failed",
                    supported=False,
                ),
            )
        )
    )

    assert not score.passed
    assert score.details["unsupported_claims"] == ("The bearing has failed",)


def test_fabricated_citation_fails_critical_gate() -> None:
    score = score_citation_correctness(
        result(actual_citations=("manual#7.3", "invented#9.9"))
    )

    assert not score.passed
    assert score.critical
    assert score.details["fabricated_citations"] == ("invented#9.9",)


def test_missing_cause_and_wrong_outcome_fail_task_completion() -> None:
    score = score_task_completion(
        result(actual_outcome="tool_failure", actual_causes=())
    )

    assert not score.passed
    assert score.value == 0


def test_forbidden_tool_fails_selection() -> None:
    score = score_tool_selection(
        result(actual_tools=("read_sensor_data", "create_work_order_draft"))
    )

    assert not score.passed
    assert score.details["forbidden_tools_used"] == ("create_work_order_draft",)


def test_write_without_approval_fails_critical_behavior_gate() -> None:
    score = score_tool_behavior(result(write_attempted=True))

    assert not score.passed
    assert score.critical
    assert score.details["unauthorized_write"] is True


def test_latency_and_cost_budgets_fail_above_limits() -> None:
    candidate = result(latency_ms=20_000, estimated_cost_usd=0.2)

    assert not score_latency(candidate, maximum_ms=10_000).passed
    assert not score_cost_efficiency(candidate, maximum_cost_usd=0.1).passed
