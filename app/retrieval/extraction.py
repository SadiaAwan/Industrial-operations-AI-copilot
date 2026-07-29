"""Safe text extraction from manifest-controlled source documents."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.retrieval.metadata import DocumentManifest, DocumentMetadata
from app.retrieval.normalization import normalize_text

SUPPORTED_SUFFIXES = frozenset({".md", ".markdown", ".txt"})
DEFAULT_MAX_DOCUMENT_BYTES = 2_000_000


class DocumentExtractionError(ValueError):
    """Raised when a source document cannot be extracted safely."""


@dataclass(frozen=True, slots=True)
class ExtractedDocument:
    metadata: DocumentMetadata
    content: str


def _strip_markdown_front_matter(text: str) -> str:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return text
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return "\n".join(lines[index + 1 :])
    raise DocumentExtractionError("unterminated Markdown front matter")


def extract_document(
    metadata: DocumentMetadata,
    *,
    data_root: Path,
    max_document_bytes: int = DEFAULT_MAX_DOCUMENT_BYTES,
) -> ExtractedDocument:
    """Extract one UTF-8 text document below the configured data root."""

    if max_document_bytes < 1:
        raise ValueError("max_document_bytes must be positive")

    resolved_root = data_root.resolve()
    source_path = (resolved_root / metadata.path).resolve()
    if not source_path.is_relative_to(resolved_root):
        raise DocumentExtractionError("source path escapes data root")
    if source_path.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise DocumentExtractionError(
            f"unsupported document type: {source_path.suffix or '<none>'}"
        )
    if not source_path.is_file():
        raise FileNotFoundError(source_path)
    if source_path.stat().st_size > max_document_bytes:
        raise DocumentExtractionError("document exceeds configured size limit")

    try:
        raw_text = source_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        raise DocumentExtractionError("document is not valid UTF-8") from error

    if source_path.suffix.lower() in {".md", ".markdown"}:
        raw_text = _strip_markdown_front_matter(raw_text)
    content = normalize_text(raw_text)
    if not content:
        raise DocumentExtractionError("document contains no extractable text")
    return ExtractedDocument(metadata=metadata, content=content)


def extract_manifest_documents(
    manifest: DocumentManifest,
    *,
    data_root: Path,
    max_document_bytes: int = DEFAULT_MAX_DOCUMENT_BYTES,
) -> tuple[ExtractedDocument, ...]:
    """Extract all manifest documents in manifest order."""

    return tuple(
        extract_document(
            document,
            data_root=data_root,
            max_document_bytes=max_document_bytes,
        )
        for document in manifest.documents
    )
