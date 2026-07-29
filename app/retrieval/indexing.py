"""Provider-neutral conversion and batching of searchable chunks."""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.retrieval.embeddings import EmbeddedChunk


class SearchIndexDocument(BaseModel):
    """Normalized representation accepted by search-index adapters."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    chunk_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    section: str = Field(min_length=1)
    machine_type: str = Field(min_length=1)
    document_type: str = Field(min_length=1)
    revision: str = Field(min_length=1)
    status: str = Field(min_length=1)
    effective_date: str = Field(min_length=1)
    source_path: str = Field(min_length=1)
    content: str = Field(min_length=1)
    content_vector: tuple[float, ...] = Field(min_length=1)
    embedding_model: str = Field(min_length=1)

    @field_validator("content_vector")
    @classmethod
    def vector_is_finite(cls, value: tuple[float, ...]) -> tuple[float, ...]:
        if not all(math.isfinite(component) for component in value):
            raise ValueError("content_vector must contain finite values")
        return value


class IndexWriter(Protocol):
    async def upload(
        self,
        documents: Sequence[SearchIndexDocument],
    ) -> None: ...


def to_index_document(item: EmbeddedChunk) -> SearchIndexDocument:
    chunk = item.chunk
    metadata = chunk.metadata
    return SearchIndexDocument(
        chunk_id=metadata.chunk_id,
        document_id=metadata.document_id,
        title=metadata.title,
        section=metadata.section,
        machine_type=metadata.machine_type,
        document_type=metadata.document_type,
        revision=metadata.revision,
        status=metadata.status.value,
        effective_date=metadata.effective_date.isoformat(),
        source_path=metadata.source_path,
        content=chunk.content,
        content_vector=item.vector,
        embedding_model=item.embedding_model,
    )


def build_index_documents(
    chunks: Sequence[EmbeddedChunk],
) -> tuple[SearchIndexDocument, ...]:
    """Convert chunks and reject duplicate search keys or mixed dimensions."""

    documents = tuple(to_index_document(chunk) for chunk in chunks)
    chunk_ids = [document.chunk_id for document in documents]
    if len(chunk_ids) != len(set(chunk_ids)):
        raise ValueError("index documents contain duplicate chunk IDs")
    dimensions = {len(document.content_vector) for document in documents}
    if len(dimensions) > 1:
        raise ValueError("index documents contain mixed vector dimensions")
    return documents


async def upload_index_documents(
    writer: IndexWriter,
    documents: Sequence[SearchIndexDocument],
    *,
    batch_size: int = 100,
) -> int:
    """Upload documents in bounded batches and return the uploaded count."""

    if batch_size < 1 or batch_size > 1_000:
        raise ValueError("batch_size must be between 1 and 1000")
    uploaded = 0
    for offset in range(0, len(documents), batch_size):
        batch = documents[offset : offset + batch_size]
        await writer.upload(batch)
        uploaded += len(batch)
    return uploaded


class InMemoryIndexWriter:
    """Deterministic index adapter for tests and local development."""

    def __init__(self) -> None:
        self.documents: dict[str, SearchIndexDocument] = {}

    async def upload(
        self,
        documents: Sequence[SearchIndexDocument],
    ) -> None:
        for document in documents:
            self.documents[document.chunk_id] = document
