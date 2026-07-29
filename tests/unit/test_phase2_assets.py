"""Validate the committed synthetic documents and evaluation seeds."""

import json
from pathlib import Path

DATA_ROOT = Path(__file__).resolve().parents[2] / "data"
EVALUATION_ROOT = Path(__file__).resolve().parents[2] / "evaluation" / "datasets"


def test_document_manifest_references_existing_unique_documents() -> None:
    manifest = json.loads(
        (DATA_ROOT / "documents_manifest.json").read_text(encoding="utf-8")
    )
    documents = manifest["documents"]
    document_ids = [item["document_id"] for item in documents]

    assert len(documents) >= 8
    assert len(document_ids) == len(set(document_ids))
    assert all((DATA_ROOT / item["path"]).is_file() for item in documents)


def test_document_collection_has_required_approved_types() -> None:
    documents = json.loads(
        (DATA_ROOT / "documents_manifest.json").read_text(encoding="utf-8")
    )["documents"]
    approved = [item for item in documents if item["status"] == "approved"]

    assert sum(item["document_type"] == "manual" for item in approved) >= 2
    assert sum(item["document_type"] == "procedure" for item in approved) >= 3
    assert sum(item["document_type"] == "safety_instruction" for item in approved) >= 2


def test_superseded_manual_points_to_current_approved_revision() -> None:
    documents = json.loads(
        (DATA_ROOT / "documents_manifest.json").read_text(encoding="utf-8")
    )["documents"]
    by_id = {item["document_id"]: item for item in documents}
    old_manual = by_id["pump_maintenance_manual_v1"]
    current_manual = by_id[old_manual["superseded_by"]]

    assert old_manual["status"] == "superseded"
    assert current_manual["status"] == "approved"
    assert current_manual["revision"] == "2.1"


def test_initial_evaluation_dataset_contains_25_unique_cases() -> None:
    case_ids: list[str] = []
    for path in sorted(EVALUATION_ROOT.glob("*_cases.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["dataset_id"]
        assert payload["purpose"]
        assert len(payload["cases"]) == 5
        case_ids.extend(item["case_id"] for item in payload["cases"])

    assert len(case_ids) == 25
    assert len(case_ids) == len(set(case_ids))
