"""Tests for manifest validation, extraction, chunking, and indexing."""

import asyncio
import json
from datetime import date
from pathlib import Path

import pytest

from app.retrieval.chunking import chunk_documents
from app.retrieval.embeddings import DeterministicHashEmbedding, embed_chunks
from app.retrieval.extraction import extract_manifest_documents
from app.retrieval.indexing import (
    InMemoryIndexWriter,
    build_index_documents,
    upload_index_documents,
)
from app.retrieval.metadata import DocumentManifest, load_manifest
from app.retrieval.revision_filtering import (
    select_indexable_documents,
    validate_revision_graph,
)

DATA_ROOT = Path(__file__).resolve().parents[2] / "data"
EFFECTIVE_ON = date(2026, 7, 29)


def _approved_manifest() -> DocumentManifest:
    manifest = load_manifest(DATA_ROOT / "documents_manifest.json")
    approved = select_indexable_documents(manifest, as_of=EFFECTIVE_ON)
    return DocumentManifest(documents=approved)


def test_manifest_and_revision_graph_are_valid() -> None:
    manifest = load_manifest(DATA_ROOT / "documents_manifest.json")

    validate_revision_graph(manifest)
    selected = select_indexable_documents(manifest, as_of=EFFECTIVE_ON)

    assert len(manifest.documents) == 8
    assert len(selected) == 7
    assert "pump_maintenance_manual_v1" not in {
        document.document_id for document in selected
    }


def test_extraction_removes_front_matter_and_preserves_sections() -> None:
    documents = extract_manifest_documents(
        _approved_manifest(),
        data_root=DATA_ROOT,
    )
    maintenance_manual = next(
        document
        for document in documents
        if document.metadata.document_id == "pump_maintenance_manual_v2"
    )

    assert not maintenance_manual.content.startswith("---")
    assert "## 7.3 Bearing vibration and temperature" in maintenance_manual.content


def test_chunking_is_deterministic_and_section_aware() -> None:
    documents = extract_manifest_documents(
        _approved_manifest(),
        data_root=DATA_ROOT,
    )
    first = chunk_documents(documents)
    second = chunk_documents(documents)

    assert first == second
    assert len(first) == 26
    assert len({chunk.metadata.chunk_id for chunk in first}) == len(first)
    assert any(
        chunk.metadata.document_id == "pump_maintenance_manual_v2"
        and chunk.metadata.section == "7.3 Bearing vibration and temperature"
        for chunk in first
    )
    assert all(chunk.character_count <= 1_200 for chunk in first)


def test_embedding_and_index_upload_are_bounded() -> None:
    async def exercise_pipeline() -> None:
        documents = extract_manifest_documents(
            _approved_manifest(),
            data_root=DATA_ROOT,
        )
        chunks = chunk_documents(documents)
        provider = DeterministicHashEmbedding(dimensions=64)
        embedded = await embed_chunks(provider, chunks, batch_size=4)
        index_documents = build_index_documents(embedded)
        writer = InMemoryIndexWriter()

        uploaded = await upload_index_documents(
            writer,
            index_documents,
            batch_size=5,
        )

        assert uploaded == len(index_documents)
        assert len(writer.documents) == len(index_documents)
        assert {len(item.content_vector) for item in index_documents} == {64}

    asyncio.run(exercise_pipeline())


def test_manifest_rejects_duplicate_document_ids() -> None:
    payload = json.loads(
        (DATA_ROOT / "documents_manifest.json").read_text(encoding="utf-8")
    )
    payload["documents"].append(payload["documents"][0])

    with pytest.raises(ValueError, match="unique"):
        DocumentManifest.model_validate(payload)


@pytest.mark.parametrize(
    ("batch_size", "message"),
    [(0, "between 1 and 1000"), (1_001, "between 1 and 1000")],
)
def test_index_upload_rejects_invalid_batch_sizes(
    batch_size: int,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        asyncio.run(
            upload_index_documents(
                InMemoryIndexWriter(),
                (),
                batch_size=batch_size,
            )
        )
