"""Stable JSON report serialization for CI artifacts and audit records."""

from __future__ import annotations

import json
from pathlib import Path

from app.evaluation.models import EvaluationReport


def render_report(report: EvaluationReport) -> str:
    return (
        json.dumps(
            report.model_dump(mode="json"),
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
        )
        + "\n"
    )


def write_report(report: EvaluationReport, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(render_report(report), encoding="utf-8")
    temporary.replace(path)
