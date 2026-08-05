"""Integration tests for evaluation CLI reports and exit codes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.run_evaluation import main

DATASET = Path("evaluation/expected_outputs/phase11_reference_results.json")


def test_cli_writes_passing_report(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    output = tmp_path / "report.json"

    exit_code = main(["--dataset", str(DATASET), "--output", str(output)])

    assert exit_code == 0
    assert json.loads(output.read_text(encoding="utf-8"))["passed"] is True
    assert "EVALUATION PASSED" in capsys.readouterr().out


def test_cli_returns_failure_for_invalid_dataset(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    invalid = tmp_path / "invalid.json"
    invalid.write_text("{}", encoding="utf-8")

    exit_code = main(["--dataset", str(invalid), "--output", str(tmp_path / "x")])

    assert exit_code == 1
    assert "EVALUATION FAILED" in capsys.readouterr().err
