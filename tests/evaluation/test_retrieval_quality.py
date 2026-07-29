"""Deterministic retrieval quality gate for the initial phase-2 dataset."""

import asyncio
import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from app.retrieval.chunking import chunk_documents
from app.retrieval.embeddings import DeterministicHashEmbedding, embed_chunks
from app.retrieval.extraction import extract_manifest_documents
from app.retrieval.hybrid_search import LocalHybridSearch, SearchFilters
from app.retrieval.metadata import DocumentManifest, load_manifest
from app.retrieval.revision_filtering import select_indexable_documents
from evaluation.scorers.retrieval_metrics import score_retrieval

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = PROJECT_ROOT / "data"
DATASET_PATH = PROJECT_ROOT / "evaluation" / "datasets" / "retrieval_cases.json"
EFFECTIVE_ON = date(2026, 7, 29)


async def _run_retrieval_cases() -> list[tuple[dict[str, Any], tuple[str, ...]]]:
    manifest = load_manifest(DATA_ROOT / "documents_manifest.json")
    approved = select_indexable_documents(manifest, as_of=EFFECTIVE_ON)
    documents = extract_manifest_documents(
        DocumentManifest(documents=approved),
        data_root=DATA_ROOT,
    )
    chunks = chunk_documents(documents)
    provider = DeterministicHashEmbedding(dimensions=128)
    embedded = await embed_chunks(provider, chunks)
    engine = LocalHybridSearch(
        chunks=embedded,
        embedding_provider=provider,
    )
    cases: list[dict[str, Any]] = json.loads(DATASET_PATH.read_text(encoding="utf-8"))[
        "cases"
    ]

    results: list[tuple[dict[str, Any], tuple[str, ...]]] = []
    for case in cases:
        hits = await engine.search(
            case["question"],
            top_k=5,
            filters=SearchFilters(
                machine_type="centrifugal_pump",
                effective_on=EFFECTIVE_ON,
            ),
        )
        references = tuple(
            (
                f"{hit.embedded_chunk.chunk.metadata.document_id}"
                f"#{hit.embedded_chunk.chunk.metadata.section}"
            )
            for hit in hits
        )
        results.append((case, references))
    return results


def test_initial_retrieval_recall_at_five_gate() -> None:
    case_results = asyncio.run(_run_retrieval_cases())
    metrics = [
        score_retrieval(
            expected_references=(
                f"{case['expected_document']}#{case['expected_section']}",
            ),
            retrieved_references=references,
            k=5,
        )
        for case, references in case_results
    ]
    average_recall = sum(item.recall_at_k for item in metrics) / len(metrics)
    mean_reciprocal_rank = sum(item.reciprocal_rank for item in metrics) / len(metrics)

    assert average_recall >= 0.90
    assert mean_reciprocal_rank >= 0.50


def test_initial_retrieval_never_returns_superseded_manual() -> None:
    case_results = asyncio.run(_run_retrieval_cases())

    assert all(
        not reference.startswith("pump_maintenance_manual_v1#")
        for _, references in case_results
        for reference in references
    )


def test_retrieval_metric_rejects_invalid_inputs() -> None:
    with pytest.raises(ValueError, match="positive"):
        score_retrieval(
            expected_references=("manual#7.3",),
            retrieved_references=(),
            k=0,
        )
    with pytest.raises(ValueError, match="must not be empty"):
        score_retrieval(
            expected_references=(),
            retrieved_references=(),
            k=5,
        )
