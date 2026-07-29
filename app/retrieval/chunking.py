"""Section-aware, deterministic chunking for technical documents."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from app.retrieval.extraction import ExtractedDocument
from app.retrieval.metadata import ChunkMetadata
from app.retrieval.normalization import normalize_heading, normalize_text

_MARKDOWN_HEADING = re.compile(r"^(?P<level>#{1,6})\s+(?P<title>.+?)\s*$")


@dataclass(frozen=True, slots=True)
class DocumentChunk:
    metadata: ChunkMetadata
    content: str
    character_count: int


def _stable_chunk_id(
    document: ExtractedDocument,
    *,
    section: str,
    part_index: int,
    content: str,
) -> str:
    identity = "\x1f".join(
        (
            document.metadata.document_id,
            document.metadata.revision,
            section,
            str(part_index),
            content,
        )
    )
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]
    return f"{document.metadata.document_id}-{digest}"


def _sections(content: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    current_heading = "Document overview"
    current_lines: list[str] = []

    def finish_section() -> None:
        body = normalize_text("\n".join(current_lines))
        if body:
            sections.append((current_heading, body))

    for line in content.splitlines():
        match = _MARKDOWN_HEADING.match(line)
        if match is None:
            current_lines.append(line)
            continue

        level = len(match.group("level"))
        heading = normalize_heading(match.group("title"))
        if level == 1 and not current_lines and not sections:
            continue
        finish_section()
        current_heading = heading
        current_lines = []

    finish_section()
    return sections


def _split_long_text(
    text: str,
    *,
    max_characters: int,
    overlap_characters: int,
) -> list[str]:
    if len(text) <= max_characters:
        return [text]

    parts: list[str] = []
    start = 0
    while start < len(text):
        target_end = min(start + max_characters, len(text))
        end = target_end
        if target_end < len(text):
            candidates = (
                text.rfind("\n\n", start, target_end),
                text.rfind(". ", start, target_end),
                text.rfind(" ", start, target_end),
            )
            boundary = max(candidates)
            if boundary > start + max_characters // 2:
                end = boundary + (1 if text[boundary] == "." else 0)
        part = text[start:end].strip()
        if part:
            parts.append(part)
        if end >= len(text):
            break
        next_start = max(end - overlap_characters, start + 1)
        while next_start < end and not text[next_start].isspace():
            next_start += 1
        start = next_start
    return parts


def chunk_document(
    document: ExtractedDocument,
    *,
    max_characters: int = 1_200,
    overlap_characters: int = 150,
) -> tuple[DocumentChunk, ...]:
    """Chunk a document by section, splitting only oversized sections."""

    if max_characters < 100:
        raise ValueError("max_characters must be at least 100")
    if overlap_characters < 0 or overlap_characters >= max_characters:
        raise ValueError("overlap_characters must be between 0 and max_characters")

    chunks: list[DocumentChunk] = []
    for section, body in _sections(document.content):
        searchable_text = normalize_text(f"{section}\n\n{body}")
        parts = _split_long_text(
            searchable_text,
            max_characters=max_characters,
            overlap_characters=overlap_characters,
        )
        for part_index, part in enumerate(parts):
            chunk_id = _stable_chunk_id(
                document,
                section=section,
                part_index=part_index,
                content=part,
            )
            metadata = ChunkMetadata.from_document(
                document.metadata,
                chunk_id=chunk_id,
                section=section,
            )
            chunks.append(
                DocumentChunk(
                    metadata=metadata,
                    content=part,
                    character_count=len(part),
                )
            )
    if not chunks:
        document_id = document.metadata.document_id
        raise ValueError(f"document produced no chunks: {document_id}")
    return tuple(chunks)


def chunk_documents(
    documents: tuple[ExtractedDocument, ...],
    *,
    max_characters: int = 1_200,
    overlap_characters: int = 150,
) -> tuple[DocumentChunk, ...]:
    """Chunk multiple documents in their supplied order."""

    return tuple(
        chunk
        for document in documents
        for chunk in chunk_document(
            document,
            max_characters=max_characters,
            overlap_characters=overlap_characters,
        )
    )
