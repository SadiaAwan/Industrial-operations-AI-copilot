"""Build local search artifacts or upload the approved corpus to Azure AI Search."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from app.retrieval.azure_search import AzureSearchClient, AzureSearchConfig
from app.retrieval.chunking import chunk_documents
from app.retrieval.embeddings import (
    DeterministicHashEmbedding,
    EmbeddingProvider,
    embed_chunks,
)
from app.retrieval.extraction import extract_manifest_documents
from app.retrieval.indexing import (
    SearchIndexDocument,
    build_index_documents,
    upload_index_documents,
)
from app.retrieval.metadata import DocumentManifest, load_manifest
from app.retrieval.revision_filtering import select_indexable_documents

DEFAULT_DATA_ROOT = Path(__file__).resolve().parents[1] / "data"


async def prepare_index_documents(
    *,
    data_root: Path,
    embedding_provider: EmbeddingProvider,
    effective_on: date,
) -> tuple[SearchIndexDocument, ...]:
    """Run manifest validation, extraction, chunking, and embedding."""

    manifest = load_manifest(data_root / "documents_manifest.json")
    approved = select_indexable_documents(manifest, as_of=effective_on)
    approved_manifest = DocumentManifest(documents=approved)
    extracted = extract_manifest_documents(
        approved_manifest,
        data_root=data_root,
    )
    chunks = chunk_documents(extracted)
    embedded = await embed_chunks(embedding_provider, chunks)
    return build_index_documents(embedded)


def write_local_artifact(
    path: Path,
    documents: Sequence[SearchIndexDocument],
) -> None:
    """Write deterministic JSON suitable for local inspection and tests."""

    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "document_count": len(documents),
        "documents": [document.model_dump(mode="json") for document in documents],
    }
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def azure_config_from_environment() -> AzureSearchConfig:
    """Load Azure settings without accepting credentials as CLI arguments."""

    endpoint = os.environ.get("AZURE_SEARCH_ENDPOINT")
    index_name = os.environ.get("AZURE_SEARCH_INDEX_NAME")
    api_key = os.environ.get("AZURE_SEARCH_API_KEY")
    bearer_token = os.environ.get("AZURE_SEARCH_BEARER_TOKEN")
    missing = [
        name
        for name, value in (
            ("AZURE_SEARCH_ENDPOINT", endpoint),
            ("AZURE_SEARCH_INDEX_NAME", index_name),
        )
        if not value
    ]
    if missing:
        raise ValueError(f"missing Azure Search settings: {', '.join(missing)}")
    return AzureSearchConfig(
        endpoint=endpoint or "",
        index_name=index_name or "",
        api_key=api_key,
        bearer_token=bearer_token,
    )


async def run(args: argparse.Namespace) -> int:
    provider = DeterministicHashEmbedding(dimensions=args.vector_dimensions)
    documents = await prepare_index_documents(
        data_root=args.data_root,
        embedding_provider=provider,
        effective_on=args.effective_on,
    )

    if args.target == "local":
        write_local_artifact(args.output, documents)
        return len(documents)

    config = azure_config_from_environment()
    async with AzureSearchClient(config) as client:
        await client.create_or_update_index(
            vector_dimensions=provider.dimensions,
        )
        return await upload_index_documents(client, documents)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-root",
        type=Path,
        default=DEFAULT_DATA_ROOT,
    )
    parser.add_argument(
        "--effective-on",
        type=date.fromisoformat,
        default=date(2026, 7, 29),
    )
    parser.add_argument(
        "--vector-dimensions",
        type=int,
        default=128,
    )
    parser.add_argument(
        "--target",
        choices=("local", "azure"),
        default="local",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_DATA_ROOT / "index_artifacts" / "search_documents.json",
    )
    return parser.parse_args()


def main() -> None:
    document_count = asyncio.run(run(parse_args()))
    print(f"indexed_documents={document_count}")


if __name__ == "__main__":
    main()
