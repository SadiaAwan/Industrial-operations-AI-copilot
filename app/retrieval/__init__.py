"""Public retrieval interfaces for ingestion, search, and citations."""

from app.retrieval.chunking import DocumentChunk, chunk_document, chunk_documents
from app.retrieval.citations import Citation, citation_from_chunk, verify_citations
from app.retrieval.embeddings import (
    DeterministicHashEmbedding,
    EmbeddedChunk,
    EmbeddingProvider,
    embed_chunks,
)
from app.retrieval.extraction import (
    DocumentExtractionError,
    ExtractedDocument,
    extract_document,
    extract_manifest_documents,
)
from app.retrieval.hybrid_search import (
    LocalHybridSearch,
    SearchFilters,
    SearchResult,
)
from app.retrieval.indexing import (
    IndexWriter,
    SearchIndexDocument,
    build_index_documents,
    upload_index_documents,
)
from app.retrieval.metadata import (
    ChunkMetadata,
    DocumentManifest,
    DocumentMetadata,
    DocumentStatus,
    load_manifest,
)

__all__ = [
    "ChunkMetadata",
    "Citation",
    "DeterministicHashEmbedding",
    "DocumentChunk",
    "DocumentExtractionError",
    "DocumentManifest",
    "DocumentMetadata",
    "DocumentStatus",
    "EmbeddedChunk",
    "EmbeddingProvider",
    "ExtractedDocument",
    "IndexWriter",
    "LocalHybridSearch",
    "SearchFilters",
    "SearchIndexDocument",
    "SearchResult",
    "build_index_documents",
    "chunk_document",
    "chunk_documents",
    "citation_from_chunk",
    "embed_chunks",
    "extract_document",
    "extract_manifest_documents",
    "load_manifest",
    "upload_index_documents",
    "verify_citations",
]
