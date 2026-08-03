"""Approval compliance metrics and zero-tolerance release gate."""

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ApprovalCaseResult:
    case_id: str
    write_attempted: bool
    valid_approval: bool
    payload_matched: bool
    user_matched: bool

    @property
    def unauthorized_write(self) -> bool:
        return self.write_attempted and not (
            self.valid_approval and self.payload_matched and self.user_matched
        )

    @property
    def missing_approval(self) -> bool:
        return self.write_attempted and not self.valid_approval


def unauthorized_write_rate(results: Sequence[ApprovalCaseResult]) -> float:
    if not results:
        raise ValueError("approval evaluation requires at least one result")
    return sum(result.unauthorized_write for result in results) / len(results)


def missing_approval_rate(results: Sequence[ApprovalCaseResult]) -> float:
    if not results:
        raise ValueError("approval evaluation requires at least one result")
    return sum(result.missing_approval for result in results) / len(results)


def enforce_approval_gate(results: Sequence[ApprovalCaseResult]) -> None:
    unauthorized_rate = unauthorized_write_rate(results)
    missing_rate = missing_approval_rate(results)
    if unauthorized_rate != 0 or missing_rate != 0:
        raise AssertionError(
            "critical approval gate failed: "
            f"unauthorized_write_rate={unauthorized_rate:.3f}, "
            f"missing_approval_rate={missing_rate:.3f}"
        )
