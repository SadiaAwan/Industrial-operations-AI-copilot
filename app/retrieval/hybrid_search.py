"""Provider-neutral hybrid keyword and vector retrieval."""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from pydantic import BaseModel, ConfigDict

from app.retrieval.embeddings import (
    EmbeddedChunk,
    EmbeddingProvider,
    cosine_similarity,
)
from app.retrieval.metadata import DocumentStatus

_TOKEN = re.compile(r"[\w.-]+", flags=re.UNICODE)


class SearchFilters(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    machine_type: str | None = None
    document_types: tuple[str, ...] = ()
    document_ids: tuple[str, ...] = ()
    effective_on: date | None = None


@dataclass(frozen=True, slots=True)
class SearchResult:
    embedded_chunk: EmbeddedChunk
    score: float
    keyword_rank: int | None
    vector_rank: int | None

    @property
    def chunk_id(self) -> str:
        return self.embedded_chunk.chunk.metadata.chunk_id


def _tokens(text: str) -> tuple[str, ...]:
    return tuple(_TOKEN.findall(text.casefold()))


def _matches_filters(item: EmbeddedChunk, filters: SearchFilters) -> bool:
    metadata = item.chunk.metadata
    effective_on = filters.effective_on or date.today()
    if metadata.status != DocumentStatus.APPROVED:
        return False
    if metadata.effective_date > effective_on:
        return False
    if filters.machine_type and metadata.machine_type != filters.machine_type:
        return False
    if filters.document_types and metadata.document_type not in filters.document_types:
        return False
    return not (
        filters.document_ids and metadata.document_id not in filters.document_ids
    )


def _keyword_scores(
    query: str,
    candidates: Sequence[EmbeddedChunk],
) -> dict[str, float]:
    query_terms = Counter(_tokens(query))
    if not query_terms:
        return {}

    document_terms = [
        Counter(_tokens(candidate.chunk.content)) for candidate in candidates
    ]
    document_frequency = {
        term: sum(term in terms for terms in document_terms) for term in query_terms
    }
    scores: dict[str, float] = {}
    for candidate, terms in zip(candidates, document_terms, strict=True):
        score = 0.0
        for term, query_count in query_terms.items():
            term_count = terms.get(term, 0)
            if term_count == 0:
                continue
            inverse_frequency = math.log(
                (len(candidates) + 1) / (document_frequency[term] + 0.5)
            )
            score += query_count * (1 + math.log(term_count)) * inverse_frequency
        if score > 0:
            scores[candidate.chunk.metadata.chunk_id] = score
    return scores


def _rank(
    scores: dict[str, float],
) -> dict[str, int]:
    ordered = sorted(scores, key=lambda item: (-scores[item], item))
    return {chunk_id: rank for rank, chunk_id in enumerate(ordered, start=1)}


class LocalHybridSearch:
    """Hybrid retrieval used for deterministic local tests and evaluation."""

    def __init__(
        self,
        *,
        chunks: Sequence[EmbeddedChunk],
        embedding_provider: EmbeddingProvider,
        rrf_constant: int = 60,
    ) -> None:
        if rrf_constant < 1:
            raise ValueError("rrf_constant must be positive")
        if any(len(item.vector) != embedding_provider.dimensions for item in chunks):
            raise ValueError("chunk and query embedding dimensions must match")
        self._chunks = tuple(chunks)
        self._embedding_provider = embedding_provider
        self._rrf_constant = rrf_constant

    async def search(
        self,
        query: str,
        *,
        top_k: int = 5,
        filters: SearchFilters | None = None,
    ) -> tuple[SearchResult, ...]:
        if not query.strip():
            raise ValueError("query must not be empty")
        if top_k < 1 or top_k > 50:
            raise ValueError("top_k must be between 1 and 50")

        active_filters = filters or SearchFilters()
        candidates = tuple(
            item for item in self._chunks if _matches_filters(item, active_filters)
        )
        if not candidates:
            return ()

        keyword_scores = _keyword_scores(query, candidates)
        keyword_ranks = _rank(keyword_scores)
        query_vectors = await self._embedding_provider.embed([query])
        if len(query_vectors) != 1:
            raise ValueError("embedding provider must return one query vector")
        query_vector = query_vectors[0]
        if len(query_vector) != self._embedding_provider.dimensions:
            raise ValueError("query embedding has an unexpected dimension")

        vector_scores = {
            item.chunk.metadata.chunk_id: cosine_similarity(
                query_vector,
                item.vector,
            )
            for item in candidates
        }
        vector_ranks = _rank(vector_scores)
        by_id = {item.chunk.metadata.chunk_id: item for item in candidates}

        results: list[SearchResult] = []
        for chunk_id in by_id:
            keyword_rank = keyword_ranks.get(chunk_id)
            vector_rank = vector_ranks.get(chunk_id)
            score = 0.0
            if keyword_rank is not None:
                score += 1 / (self._rrf_constant + keyword_rank)
            if vector_rank is not None:
                score += 1 / (self._rrf_constant + vector_rank)
            results.append(
                SearchResult(
                    embedded_chunk=by_id[chunk_id],
                    score=score,
                    keyword_rank=keyword_rank,
                    vector_rank=vector_rank,
                )
            )

        results.sort(key=lambda result: (-result.score, result.chunk_id))
        return tuple(results[:top_k])
