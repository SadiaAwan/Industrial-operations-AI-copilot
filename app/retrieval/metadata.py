"""Validated metadata contracts for source documents and retrieval chunks."""

from __future__ import annotations

import json
from datetime import date
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DocumentStatus(StrEnum):
    APPROVED = "approved"
    SUPERSEDED = "superseded"
    DRAFT = "draft"


class DocumentMetadata(BaseModel):
    """Governance metadata loaded from the document manifest."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    document_id: str = Field(min_length=1)
    path: str = Field(min_length=1)
    title: str = Field(min_length=1)
    document_type: str = Field(min_length=1)
    machine_type: str = Field(min_length=1)
    revision: str = Field(min_length=1)
    status: DocumentStatus
    effective_date: date
    supersedes: str | None = None
    superseded_by: str | None = None

    @model_validator(mode="after")
    def validate_revision_relationship(self) -> DocumentMetadata:
        if self.status == DocumentStatus.SUPERSEDED and not self.superseded_by:
            raise ValueError("superseded documents must identify superseded_by")
        if self.status == DocumentStatus.APPROVED and self.superseded_by:
            raise ValueError("approved documents cannot identify superseded_by")
        if Path(self.path).is_absolute() or ".." in Path(self.path).parts:
            raise ValueError("document path must be relative to the data directory")
        return self

    @property
    def is_approved(self) -> bool:
        return self.status == DocumentStatus.APPROVED


class DocumentManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    documents: tuple[DocumentMetadata, ...]

    @model_validator(mode="after")
    def document_ids_are_unique(self) -> DocumentManifest:
        document_ids = [document.document_id for document in self.documents]
        if len(document_ids) != len(set(document_ids)):
            raise ValueError("document IDs must be unique")
        return self

    def by_id(self) -> dict[str, DocumentMetadata]:
        return {document.document_id: document for document in self.documents}


class ChunkMetadata(BaseModel):
    """Metadata retained on every searchable chunk."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    chunk_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    section: str = Field(min_length=1)
    machine_type: str = Field(min_length=1)
    document_type: str = Field(min_length=1)
    revision: str = Field(min_length=1)
    status: DocumentStatus
    effective_date: date
    source_path: str = Field(min_length=1)

    @classmethod
    def from_document(
        cls,
        document: DocumentMetadata,
        *,
        chunk_id: str,
        section: str,
    ) -> ChunkMetadata:
        return cls(
            chunk_id=chunk_id,
            document_id=document.document_id,
            title=document.title,
            section=section,
            machine_type=document.machine_type,
            document_type=document.document_type,
            revision=document.revision,
            status=document.status,
            effective_date=document.effective_date,
            source_path=document.path,
        )


def load_manifest(path: Path) -> DocumentManifest:
    """Load and validate a UTF-8 JSON document manifest."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    return DocumentManifest.model_validate(payload)


def validate_manifest_paths(
    manifest: DocumentManifest,
    *,
    data_root: Path,
) -> None:
    """Fail when a manifest entry does not resolve to a file below ``data_root``."""

    resolved_root = data_root.resolve()
    for document in manifest.documents:
        resolved_path = (resolved_root / document.path).resolve()
        if not resolved_path.is_relative_to(resolved_root):
            raise ValueError(f"document path escapes data root: {document.path}")
        if not resolved_path.is_file():
            raise FileNotFoundError(resolved_path)
