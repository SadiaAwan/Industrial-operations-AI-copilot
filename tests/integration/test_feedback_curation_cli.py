from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.curate_feedback_eval_cases import main

PROMPT_DIGEST = "e45959a50682bc17822873a90070a9dcb08208b935415f4aa1ad1aed0e26abeb"


def _record(*, reviewed: bool = True) -> dict[str, object]:
    return {
        "feedback_id": "FEEDBACK-1",
        "session_id": "SESSION-PRIVATE",
        "trace_id": "TRACE-1",
        "rating": "not_helpful",
        "agent_version": "phase-12",
        "prompt_version": "diagnostics-v1",
        "prompt_sha256": PROMPT_DIGEST,
        "reviewed": reviewed,
        "include_in_evaluation": True,
        "case_id": "FEEDBACK-EVAL-1",
        "expected_outcome": "completed",
        "expected_causes": ["bearing degradation"],
        "expected_tools": ["read_sensor_data"],
    }


def test_cli_writes_privacy_safe_versioned_dataset(tmp_path: Path) -> None:
    source = tmp_path / "reviewed.json"
    output = tmp_path / "dataset.json"
    source.write_text(json.dumps([_record()]), encoding="utf-8")

    exit_code = main(
        [
            "--input",
            str(source),
            "--output",
            str(output),
            "--dataset-id",
            "feedback-regressions",
            "--dataset-version",
            "1.0.0",
        ]
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert payload["dataset_version"] == "1.0.0"
    assert payload["cases"][0]["source_trace_id"] == "TRACE-1"
    assert "SESSION-PRIVATE" not in output.read_text(encoding="utf-8")


def test_cli_rejects_unreviewed_feedback(tmp_path: Path) -> None:
    source = tmp_path / "unreviewed.json"
    source.write_text(json.dumps([_record(reviewed=False)]), encoding="utf-8")

    with pytest.raises(SystemExit, match="human review"):
        main(
            [
                "--input",
                str(source),
                "--output",
                str(tmp_path / "should-not-exist.json"),
                "--dataset-id",
                "feedback-regressions",
                "--dataset-version",
                "1.0.0",
            ]
        )
