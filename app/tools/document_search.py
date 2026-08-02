"""Grounded technical-document search tool."""

from typing import Protocol

from app.retrieval.citations import citation_from_chunk
from app.retrieval.hybrid_search import SearchFilters, SearchResult
from app.schemas.tools import (
    DocumentSearchOutput,
    DocumentSearchQuery,
    ToolResult,
)
from app.tools.runtime import ToolExecutor


class DocumentSearchBackend(Protocol):
    async def search(
        self,
        query: str,
        *,
        top_k: int = 5,
        filters: SearchFilters | None = None,
    ) -> tuple[SearchResult, ...]: ...


class DocumentSearchTool:
    name = "search_technical_documents"

    def __init__(
        self,
        backend: DocumentSearchBackend,
        *,
        executor: ToolExecutor | None = None,
    ) -> None:
        self._backend = backend
        self._executor = executor or ToolExecutor()

    async def __call__(
        self, request: DocumentSearchQuery
    ) -> ToolResult[tuple[DocumentSearchOutput, ...]]:
        async def operation() -> tuple[DocumentSearchOutput, ...]:
            results = await self._backend.search(
                request.query,
                top_k=min(request.limit, 50),
                filters=SearchFilters(machine_type=request.machine_type),
            )
            return tuple(
                DocumentSearchOutput(
                    content=result.embedded_chunk.chunk.content,
                    score=result.score,
                    citation=citation_from_chunk(result.embedded_chunk.chunk),
                )
                for result in results
            )

        return await self._executor.execute(self.name, operation)
