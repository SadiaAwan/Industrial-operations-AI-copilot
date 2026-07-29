"""Embedding contracts and a deterministic local implementation."""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from app.retrieval.chunking import DocumentChunk

_TOKEN = re.compile(r"[\w.-]+", flags=re.UNICODE)


class EmbeddingProvider(Protocol):
    """Provider boundary implemented by local and hosted embedding adapters."""

    @property
    def dimensions(self) -> int: ...

    @property
    def model_name(self) -> str: ...

    async def embed(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]: ...


@dataclass(frozen=True, slots=True)
class EmbeddedChunk:
    chunk: DocumentChunk
    vector: tuple[float, ...]
    embedding_model: str


class DeterministicHashEmbedding:
    """Offline feature-hashing embeddings for tests and local development.

    This implementation is not intended to represent semantic production quality.
    It provides stable vectors so ingestion, ranking, and evaluation can run without
    network or paid model calls.
    """

    def __init__(self, dimensions: int = 128) -> None:
        if dimensions < 8:
            raise ValueError("dimensions must be at least 8")
        self._dimensions = dimensions

    @property
    def dimensions(self) -> int:
        return self._dimensions

    @property
    def model_name(self) -> str:
        return f"deterministic-hash-v1-{self.dimensions}"

    async def embed(
        self,
        texts: Sequence[str],
    ) -> tuple[tuple[float, ...], ...]:
        return tuple(self._embed_one(text) for text in texts)

    def _embed_one(self, text: str) -> tuple[float, ...]:
        vector = [0.0] * self.dimensions
        tokens = _TOKEN.findall(text.casefold())
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:8], "big") % self.dimensions
            sign = 1.0 if digest[8] & 1 else -1.0
            vector[index] += sign

        magnitude = math.sqrt(sum(value * value for value in vector))
        if magnitude == 0.0:
            return tuple(vector)
        return tuple(value / magnitude for value in vector)


async def embed_chunks(
    provider: EmbeddingProvider,
    chunks: Sequence[DocumentChunk],
    *,
    batch_size: int = 32,
) -> tuple[EmbeddedChunk, ...]:
    """Embed chunks in bounded batches and validate provider output."""

    if batch_size < 1:
        raise ValueError("batch_size must be positive")

    results: list[EmbeddedChunk] = []
    for offset in range(0, len(chunks), batch_size):
        batch = chunks[offset : offset + batch_size]
        vectors = await provider.embed([chunk.content for chunk in batch])
        if len(vectors) != len(batch):
            raise ValueError("embedding provider returned an unexpected vector count")
        for chunk, vector in zip(batch, vectors, strict=True):
            if len(vector) != provider.dimensions:
                raise ValueError("embedding provider returned an unexpected dimension")
            if not all(math.isfinite(value) for value in vector):
                raise ValueError("embedding vector contains a non-finite value")
            results.append(
                EmbeddedChunk(
                    chunk=chunk,
                    vector=vector,
                    embedding_model=provider.model_name,
                )
            )
    return tuple(results)


def cosine_similarity(
    left: Sequence[float],
    right: Sequence[float],
) -> float:
    """Return cosine similarity for two finite, equal-length vectors."""

    if not left or len(left) != len(right):
        raise ValueError("vectors must be non-empty and have equal dimensions")
    if not all(math.isfinite(value) for value in (*left, *right)):
        raise ValueError("vectors must contain only finite values")

    left_magnitude = math.sqrt(sum(value * value for value in left))
    right_magnitude = math.sqrt(sum(value * value for value in right))
    if left_magnitude == 0.0 or right_magnitude == 0.0:
        return 0.0
    dot_product = sum(a * b for a, b in zip(left, right, strict=True))
    return dot_product / (left_magnitude * right_magnitude)
