"""Create a versioned, privacy-safe evaluation dataset from reviewed feedback."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from app.evaluation.feedback_cases import FeedbackCaseInput, curate_feedback_cases


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--dataset-version", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    options = _parser().parse_args(argv)
    try:
        payload = json.loads(options.input.read_text(encoding="utf-8"))
        records = TypeAdapter(tuple[FeedbackCaseInput, ...]).validate_python(payload)
        dataset = curate_feedback_cases(
            records,
            dataset_id=options.dataset_id,
            dataset_version=options.dataset_version,
            generated_at=datetime.now(UTC),
        )
    except (OSError, json.JSONDecodeError, ValidationError, ValueError) as error:
        raise SystemExit(f"feedback curation failed: {error}") from error

    options.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = options.output.with_suffix(f"{options.output.suffix}.tmp")
    temporary.write_text(dataset.model_dump_json(indent=2), encoding="utf-8")
    temporary.replace(options.output)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
