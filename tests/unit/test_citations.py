"""Tests for citation creation and source verification."""

from datetime import date

import pytest

from app.retrieval.chunking import DocumentChunk
from app.retrieval.citations import (
    Citation,
    citation_from_chunk,
    deduplicate_citations,
    verify_citations,
)
from app.retrieval.metadata import ChunkMetadata, DocumentStatus


def _chunk() -> DocumentChunk:
    content = (
        "7.3 Bearing vibration and temperature\n\n"
        "Concurrent increases can indicate bearing degradation or misalignment."
    )
    return DocumentChunk(
        metadata=ChunkMetadata(
            chunk_id="manual-v2-7-3",
            document_id="pump_maintenance_manual_v2",
            title="Centrifugal Pump Maintenance Manual",
            section="7.3 Bearing vibration and temperature",
            machine_type="centrifugal_pump",
            document_type="manual",
            revision="2.1",
            status=DocumentStatus.APPROVED,
            effective_date=date(2026, 1, 10),
            source_path="manuals/pump_manual_v2.md",
        ),
        content=content,
        character_count=len(content),
    )


def test_citation_resolves_to_exact_retrieved_chunk() -> None:
    chunk = _chunk()
    citation = citation_from_chunk(chunk)

    verify_citations([citation], retrieved_chunks=[chunk])

    assert citation.reference.startswith("pump_maintenance_manual_v2#7.3")
    assert citation.revision == "2.1"
    assert citation.excerpt


def test_citation_not_present_in_retrieval_is_rejected() -> None:
    citation = citation_from_chunk(_chunk()).model_copy(
        update={"chunk_id": "fabricated-chunk"}
    )

    with pytest.raises(ValueError, match="does not resolve"):
        verify_citations([citation], retrieved_chunks=[_chunk()])


def test_citation_with_changed_metadata_is_rejected() -> None:
    citation = citation_from_chunk(_chunk()).model_copy(update={"revision": "9.9"})

    with pytest.raises(ValueError, match="metadata mismatch"):
        verify_citations([citation], retrieved_chunks=[_chunk()])


def test_citations_are_deduplicated_by_chunk_id() -> None:
    citation = citation_from_chunk(_chunk())

    assert deduplicate_citations([citation, citation]) == (citation,)


def test_excerpt_length_is_bounded() -> None:
    citation: Citation = citation_from_chunk(
        _chunk(),
        excerpt_characters=40,
    )

    assert len(citation.excerpt) <= 40
    assert citation.excerpt.endswith("…")
