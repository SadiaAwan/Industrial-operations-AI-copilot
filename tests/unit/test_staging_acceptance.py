import json
from pathlib import Path

import pytest

from scripts.verify_staging_acceptance import REQUIRED_CHECKS, validate_staging_evidence

COMMIT = "a" * 40


def evidence() -> dict[str, object]:
    return {
        "environment": "staging",
        "commit": COMMIT,
        "api_image": f"example.azurecr.io/industrial-copilot-api@sha256:{'b' * 64}",
        "ui_image": f"example.azurecr.io/industrial-copilot-ui@sha256:{'c' * 64}",
        "checks": dict.fromkeys(REQUIRED_CHECKS, True),
        "evidence_urls": {"acceptance_run": "https://example.test/run/1"},
        "approved_by": "operator-1",
        "completed_at": "2026-08-12T12:00:00Z",
    }


def write(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_accepts_complete_staging_evidence(tmp_path: Path) -> None:
    path = tmp_path / "acceptance.json"
    write(path, evidence())

    result = validate_staging_evidence(path, expected_commit=COMMIT)

    assert result["environment"] == "staging"


@pytest.mark.parametrize("failed_check", sorted(REQUIRED_CHECKS))
def test_rejects_every_failed_acceptance_check(
    tmp_path: Path, failed_check: str
) -> None:
    payload = evidence()
    checks = payload["checks"]
    assert isinstance(checks, dict)
    checks[failed_check] = False
    path = tmp_path / "acceptance.json"
    write(path, payload)

    with pytest.raises(ValueError, match=failed_check):
        validate_staging_evidence(path, expected_commit=COMMIT)
