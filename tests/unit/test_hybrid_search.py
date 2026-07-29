"""Tests for deterministic local hybrid retrieval."""

import asyncio
from datetime import date
from pathlib import Path

import pytest

from app.retrieval.chunking import chunk_documents
from app.retrieval.embeddings import DeterministicHashEmbedding, embed_chunks
from app.retrieval.extraction import extract_manifest_documents
from app.retrieval.hybrid_search import LocalHybridSearch, SearchFilters
from app.retrieval.metadata import DocumentManifest, load_manifest
from app.retrieval.revision_filtering import select_indexable_documents

DATA_ROOT = Path(__file__).resolve().parents[2] / "data"
EFFECTIVE_ON = date(2026, 7, 29)


async def _engine() -> LocalHybridSearch:
    manifest = load_manifest(DATA_ROOT / "documents_manifest.json")
    approved = select_indexable_documents(manifest, as_of=EFFECTIVE_ON)
    extracted = extract_manifest_documents(
        DocumentManifest(documents=approved),
        data_root=DATA_ROOT,
    )
    chunks = chunk_documents(extracted)
    provider = DeterministicHashEmbedding(dimensions=128)
    embedded = await embed_chunks(provider, chunks)
    return LocalHybridSearch(
        chunks=embedded,
        embedding_provider=provider,
    )


def test_hybrid_search_returns_relevant_cavitation_section_first() -> None:
    async def search() -> None:
        engine = await _engine()
        results = await engine.search(
            "Which indicators suggest pump cavitation?",
            filters=SearchFilters(
                machine_type="centrifugal_pump",
                effective_on=EFFECTIVE_ON,
            ),
        )

        first = results[0].embedded_chunk.chunk.metadata
        assert first.document_id == "pump_maintenance_manual_v2"
        assert first.section == "6.2 Cavitation indicators"
        assert results[0].keyword_rank is not None
        assert results[0].vector_rank is not None

    asyncio.run(search())


def test_document_type_filter_limits_results() -> None:
    async def search() -> None:
        engine = await _engine()
        results = await engine.search(
            "What safety rules apply before touching the pump?",
            top_k=10,
            filters=SearchFilters(
                document_types=("safety_instruction",),
                effective_on=EFFECTIVE_ON,
            ),
        )

        assert results
        assert all(
            item.embedded_chunk.chunk.metadata.document_type == "safety_instruction"
            for item in results
        )

    asyncio.run(search())


def test_search_is_deterministic_and_excludes_superseded_revision() -> None:
    async def search() -> None:
        engine = await _engine()
        filters = SearchFilters(effective_on=EFFECTIVE_ON)
        first = await engine.search(
            "bearing vibration temperature",
            top_k=10,
            filters=filters,
        )
        second = await engine.search(
            "bearing vibration temperature",
            top_k=10,
            filters=filters,
        )

        assert first == second
        assert all(
            result.embedded_chunk.chunk.metadata.document_id
            != "pump_maintenance_manual_v1"
            for result in first
        )

    asyncio.run(search())


@pytest.mark.parametrize("top_k", [0, 51])
def test_search_rejects_invalid_result_limits(top_k: int) -> None:
    async def search() -> None:
        engine = await _engine()
        with pytest.raises(ValueError, match="top_k"):
            await engine.search("pump", top_k=top_k)

    asyncio.run(search())


def test_search_rejects_empty_query() -> None:
    async def search() -> None:
        engine = await _engine()
        with pytest.raises(ValueError, match="query"):
            await engine.search("   ")

    asyncio.run(search())
