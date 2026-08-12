"""Validate Phase 17 staging evidence against the acceptance contract."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
DIGEST_PATTERN = re.compile(
    r"^[a-z0-9.-]+\.azurecr\.io/[a-z0-9._/-]+@sha256:[0-9a-f]{64}$"
)
REQUIRED_CHECKS = {
    "api_health",
    "api_readiness",
    "ui_health",
    "database_migration",
    "document_index",
    "evaluation_gate",
    "observability",
    "least_privilege",
    "rollback_rehearsal",
    "operator_acceptance",
}


def _required(payload: dict[str, Any], name: str, expected_type: type[Any]) -> Any:
    value = payload.get(name)
    if not isinstance(value, expected_type):
        raise ValueError(f"{name} must be {expected_type.__name__}")
    return value


def validate_staging_evidence(path: Path, *, expected_commit: str) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("staging evidence must be a JSON object")
    if payload.get("environment") != "staging":
        raise ValueError("evidence must come from staging")
    commit = _required(payload, "commit", str)
    if commit != expected_commit or COMMIT_PATTERN.fullmatch(commit) is None:
        raise ValueError("evidence commit does not match the verified commit")
    for name in ("api_image", "ui_image"):
        image = _required(payload, name, str)
        if DIGEST_PATTERN.fullmatch(image) is None:
            raise ValueError(f"{name} must be an immutable ACR digest")
    checks = _required(payload, "checks", dict)
    if set(checks) != REQUIRED_CHECKS:
        raise ValueError("staging evidence checks are incomplete or unexpected")
    failed = sorted(name for name, passed in checks.items() if passed is not True)
    if failed:
        raise ValueError(f"staging acceptance failed: {', '.join(failed)}")
    _required(payload, "evidence_urls", dict)
    _required(payload, "approved_by", str)
    _required(payload, "completed_at", str)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--expected-commit", required=True)
    arguments = parser.parse_args()
    validate_staging_evidence(
        arguments.evidence, expected_commit=arguments.expected_commit
    )
    print("STAGING ACCEPTANCE PASSED")


if __name__ == "__main__":
    main()
