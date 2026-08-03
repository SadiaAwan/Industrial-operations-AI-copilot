"""Critical Phase 7 eval gates must fail on any unsafe outcome."""

import pytest

from evaluation.scorers.approval_compliance import (
    ApprovalCaseResult,
    enforce_approval_gate,
    missing_approval_rate,
    unauthorized_write_rate,
)
from evaluation.scorers.safety_compliance import (
    SafetyCaseResult,
    enforce_safety_gate,
    fabricated_citation_rate,
    unsafe_action_rate,
)


def test_safe_results_pass_zero_tolerance_gate() -> None:
    results = [
        SafetyCaseResult(
            case_id="SAFE-001",
            unsafe_action=False,
            fabricated_citation=False,
        )
    ]
    enforce_safety_gate(results)
    assert unsafe_action_rate(results) == 0
    assert fabricated_citation_rate(results) == 0


def test_single_unsafe_result_blocks_release() -> None:
    results = [
        SafetyCaseResult(
            case_id="SAFE-001",
            unsafe_action=True,
            fabricated_citation=False,
        )
    ]
    with pytest.raises(AssertionError, match="critical safety gate failed"):
        enforce_safety_gate(results)


def test_compliant_approved_write_passes_gate() -> None:
    results = [
        ApprovalCaseResult(
            case_id="APPROVAL-001",
            write_attempted=True,
            valid_approval=True,
            payload_matched=True,
            user_matched=True,
        )
    ]
    enforce_approval_gate(results)
    assert unauthorized_write_rate(results) == 0
    assert missing_approval_rate(results) == 0


@pytest.mark.parametrize(
    "result",
    [
        ApprovalCaseResult(
            case_id="APPROVAL-MISSING",
            write_attempted=True,
            valid_approval=False,
            payload_matched=True,
            user_matched=True,
        ),
        ApprovalCaseResult(
            case_id="APPROVAL-PAYLOAD",
            write_attempted=True,
            valid_approval=True,
            payload_matched=False,
            user_matched=True,
        ),
        ApprovalCaseResult(
            case_id="APPROVAL-USER",
            write_attempted=True,
            valid_approval=True,
            payload_matched=True,
            user_matched=False,
        ),
    ],
)
def test_any_unauthorized_write_blocks_release(result: ApprovalCaseResult) -> None:
    with pytest.raises(AssertionError, match="critical approval gate failed"):
        enforce_approval_gate([result])
