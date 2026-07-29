"""Deterministic text normalization for document ingestion."""

from __future__ import annotations

import re
import unicodedata

_HORIZONTAL_WHITESPACE = re.compile(r"[^\S\n]+")
_EXCESS_BLANK_LINES = re.compile(r"\n{3,}")
_HEADING_PREFIX = re.compile(r"^#{1,6}\s+")
_SECTION_NUMBER = re.compile(r"^(?P<number>\d+(?:\.\d+)*)\s*[-–—:]?\s*(?P<title>.*)$")


def normalize_text(text: str) -> str:
    """Normalize Unicode, line endings, whitespace, and blank lines."""

    normalized = unicodedata.normalize("NFC", text)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    lines = [
        _HORIZONTAL_WHITESPACE.sub(" ", line).strip() for line in normalized.split("\n")
    ]
    normalized = "\n".join(lines)
    normalized = _EXCESS_BLANK_LINES.sub("\n\n", normalized)
    return normalized.strip()


def normalize_heading(heading: str) -> str:
    """Return a plain normalized heading without Markdown markers."""

    normalized = normalize_text(heading)
    return _HEADING_PREFIX.sub("", normalized).strip()


def split_section_heading(heading: str) -> tuple[str | None, str]:
    """Split headings such as ``7.3 Bearing vibration`` into number and title."""

    normalized = normalize_heading(heading)
    match = _SECTION_NUMBER.match(normalized)
    if match is None:
        return None, normalized
    section_number = match.group("number")
    title = match.group("title").strip()
    return section_number, title or section_number
