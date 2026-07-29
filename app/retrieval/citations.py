"""Structured citations that resolve to retrieved document chunks."""

from __future__ import annotations

from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict, Field

from app.retrieval.chunking import DocumentChunk


class Citation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    chunk_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    revision: str = Field(min_length=1)
    section: str = Field(min_length=1)
    source_path: str = Field(min_length=1)
    excerpt: str = Field(min_length=1, max_length=500)

    @property
    def reference(self) -> str:
        return f"{self.document_id}#{self.section}"


def _excerpt(content: str, *, max_characters: int) -> str:
    if max_characters < 20 or max_characters > 500:
        raise ValueError("max_characters must be between 20 and 500")
    compact = " ".join(content.split())
    if len(compact) <= max_characters:
        return compact
    shortened = compact[: max_characters - 1].rsplit(" ", maxsplit=1)[0]
    return f"{shortened}…"


def citation_from_chunk(
    chunk: DocumentChunk,
    *,
    excerpt_characters: int = 240,
) -> Citation:
    metadata = chunk.metadata
    return Citation(
        chunk_id=metadata.chunk_id,
        document_id=metadata.document_id,
        title=metadata.title,
        revision=metadata.revision,
        section=metadata.section,
        source_path=metadata.source_path,
        excerpt=_excerpt(chunk.content, max_characters=excerpt_characters),
    )


def verify_citations(
    citations: Iterable[Citation],
    *,
    retrieved_chunks: Iterable[DocumentChunk],
) -> None:
    """Verify that every citation exactly matches a retrieved source chunk."""

    chunks_by_id = {chunk.metadata.chunk_id: chunk for chunk in retrieved_chunks}
    for citation in citations:
        chunk = chunks_by_id.get(citation.chunk_id)
        if chunk is None:
            raise ValueError(
                f"citation does not resolve to a retrieved chunk: {citation.chunk_id}"
            )
        metadata = chunk.metadata
        expected = (
            metadata.document_id,
            metadata.title,
            metadata.revision,
            metadata.section,
            metadata.source_path,
        )
        actual = (
            citation.document_id,
            citation.title,
            citation.revision,
            citation.section,
            citation.source_path,
        )
        if actual != expected:
            raise ValueError(f"citation metadata mismatch: {citation.chunk_id}")


def deduplicate_citations(
    citations: Iterable[Citation],
) -> tuple[Citation, ...]:
    """Keep the first occurrence of each cited chunk."""

    unique: list[Citation] = []
    seen: set[str] = set()
    for citation in citations:
        if citation.chunk_id not in seen:
            seen.add(citation.chunk_id)
            unique.append(citation)
    return tuple(unique)
