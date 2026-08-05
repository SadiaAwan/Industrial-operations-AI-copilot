"""Strict loading and fingerprinting of versioned evaluation datasets."""

from __future__ import annotations

import hashlib
from pathlib import Path

from pydantic import ValidationError

from app.evaluation.models import EvaluationDataset


class EvaluationDatasetError(ValueError):
    pass


def load_evaluation_dataset(path: Path) -> tuple[EvaluationDataset, str]:
    try:
        raw = path.read_bytes()
    except OSError as exception:
        raise EvaluationDatasetError(
            f"cannot read evaluation dataset: {path}"
        ) from exception
    try:
        dataset = EvaluationDataset.model_validate_json(raw)
    except ValidationError as exception:
        raise EvaluationDatasetError(
            f"invalid evaluation dataset: {path}"
        ) from exception
    case_ids = [result.case_id for result in dataset.results]
    if len(case_ids) != len(set(case_ids)):
        raise EvaluationDatasetError("evaluation case IDs must be unique")
    return dataset, hashlib.sha256(raw).hexdigest()
