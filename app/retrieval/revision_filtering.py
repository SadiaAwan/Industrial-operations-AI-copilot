"""Document-revision governance for indexing and retrieval."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date

from app.retrieval.chunking import DocumentChunk
from app.retrieval.metadata import (
    DocumentManifest,
    DocumentMetadata,
    DocumentStatus,
)


class RevisionGraphError(ValueError):
    """Raised when document revision relationships are inconsistent."""


def validate_revision_graph(manifest: DocumentManifest) -> None:
    """Validate supersession references and detect cycles."""

    by_id = manifest.by_id()
    for document in manifest.documents:
        for related_id in (document.supersedes, document.superseded_by):
            if related_id is not None and related_id not in by_id:
                raise RevisionGraphError(
                    f"{document.document_id} references unknown document {related_id}"
                )

        if document.supersedes is not None:
            previous = by_id[document.supersedes]
            if previous.superseded_by != document.document_id:
                raise RevisionGraphError(
                    f"{document.document_id} and {previous.document_id} "
                    "have inconsistent supersession links"
                )
            if previous.title != document.title:
                raise RevisionGraphError(
                    "superseding revisions must retain the document title"
                )

    for document in manifest.documents:
        visited: set[str] = set()
        current = document
        while current.superseded_by is not None:
            if current.document_id in visited:
                raise RevisionGraphError(
                    f"revision cycle detected at {current.document_id}"
                )
            visited.add(current.document_id)
            current = by_id[current.superseded_by]


def select_indexable_documents(
    manifest: DocumentManifest,
    *,
    as_of: date | None = None,
) -> tuple[DocumentMetadata, ...]:
    """Return approved, effective documents suitable for the normal index."""

    validate_revision_graph(manifest)
    effective_on = as_of or date.today()
    return tuple(
        document
        for document in manifest.documents
        if document.status == DocumentStatus.APPROVED
        and document.effective_date <= effective_on
        and document.superseded_by is None
    )


def filter_current_chunks(
    chunks: Iterable[DocumentChunk],
    *,
    as_of: date | None = None,
) -> tuple[DocumentChunk, ...]:
    """Apply the same approval and effective-date policy to search results."""

    effective_on = as_of or date.today()
    return tuple(
        chunk
        for chunk in chunks
        if chunk.metadata.status == DocumentStatus.APPROVED
        and chunk.metadata.effective_date <= effective_on
    )
