"""Azure AI Search adapter for index management and hybrid queries."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any

import httpx
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    field_validator,
    model_validator,
)

from app.retrieval.hybrid_search import SearchFilters
from app.retrieval.indexing import SearchIndexDocument

DEFAULT_API_VERSION = "2024-07-01"
_INDEX_NAME = re.compile(r"^[a-z0-9][a-z0-9_-]{1,127}$")


class AzureSearchConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    endpoint: str = Field(min_length=1)
    index_name: str = Field(min_length=2, max_length=128)
    api_version: str = Field(default=DEFAULT_API_VERSION, min_length=1)
    api_key: SecretStr | None = None
    bearer_token: SecretStr | None = None
    timeout_seconds: float = Field(default=10.0, gt=0, le=60)

    @field_validator("endpoint")
    @classmethod
    def normalize_endpoint(cls, value: str) -> str:
        normalized = value.rstrip("/")
        if not normalized.startswith("https://"):
            raise ValueError("Azure AI Search endpoint must use HTTPS")
        return normalized

    @field_validator("index_name")
    @classmethod
    def validate_index_name(cls, value: str) -> str:
        if _INDEX_NAME.fullmatch(value) is None:
            raise ValueError("invalid Azure AI Search index name")
        return value

    @model_validator(mode="after")
    def exactly_one_credential(self) -> AzureSearchConfig:
        if (self.api_key is None) == (self.bearer_token is None):
            raise ValueError("configure exactly one Azure AI Search credential")
        return self


class AzureSearchError(RuntimeError):
    """Raised for failed or incomplete Azure AI Search operations."""


@dataclass(frozen=True, slots=True)
class AzureSearchHit:
    document: SearchIndexDocument
    score: float


def build_index_schema(
    *,
    index_name: str,
    vector_dimensions: int,
) -> dict[str, Any]:
    """Build the Azure AI Search index definition used by this project."""

    if _INDEX_NAME.fullmatch(index_name) is None:
        raise ValueError("invalid Azure AI Search index name")
    if vector_dimensions < 8:
        raise ValueError("vector_dimensions must be at least 8")

    def string_field(name: str, **options: Any) -> dict[str, Any]:
        return {
            "name": name,
            "type": "Edm.String",
            **options,
        }

    return {
        "name": index_name,
        "fields": [
            string_field("chunk_id", key=True, filterable=True),
            string_field("document_id", filterable=True, facetable=True),
            string_field("title", searchable=True, filterable=True),
            string_field("section", searchable=True, filterable=True),
            string_field("machine_type", filterable=True, facetable=True),
            string_field("document_type", filterable=True, facetable=True),
            string_field("revision", filterable=True),
            string_field("status", filterable=True, facetable=True),
            string_field("effective_date", filterable=True, sortable=True),
            string_field("source_path", filterable=True),
            string_field("content", searchable=True),
            {
                "name": "content_vector",
                "type": "Collection(Edm.Single)",
                "searchable": True,
                "dimensions": vector_dimensions,
                "vectorSearchProfile": "default-vector-profile",
            },
            string_field("embedding_model", filterable=True),
        ],
        "vectorSearch": {
            "algorithms": [
                {
                    "name": "default-hnsw",
                    "kind": "hnsw",
                    "hnswParameters": {
                        "metric": "cosine",
                        "m": 4,
                        "efConstruction": 400,
                        "efSearch": 500,
                    },
                }
            ],
            "profiles": [
                {
                    "name": "default-vector-profile",
                    "algorithm": "default-hnsw",
                }
            ],
        },
    }


def _escape_odata(value: str) -> str:
    return value.replace("'", "''")


def build_odata_filter(filters: SearchFilters) -> str:
    """Translate safe, validated filters without accepting raw OData input."""

    clauses = ["status eq 'approved'"]
    effective_on = filters.effective_on or date.today()
    clauses.append(f"effective_date le '{effective_on.isoformat()}'")
    if filters.machine_type:
        machine_type = _escape_odata(filters.machine_type)
        clauses.append(f"machine_type eq '{machine_type}'")
    if filters.document_types:
        values = ",".join(_escape_odata(item) for item in filters.document_types)
        clauses.append(f"search.in(document_type, '{values}', ',')")
    if filters.document_ids:
        values = ",".join(_escape_odata(item) for item in filters.document_ids)
        clauses.append(f"search.in(document_id, '{values}', ',')")
    return " and ".join(clauses)


class AzureSearchClient:
    """Small async REST adapter with injectable transport for deterministic tests."""

    def __init__(
        self,
        config: AzureSearchConfig,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._config = config
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            timeout=config.timeout_seconds,
        )

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._config.api_key is not None:
            headers["api-key"] = self._config.api_key.get_secret_value()
        else:
            token = self._config.bearer_token
            if token is None:  # pragma: no cover - guarded by config validation
                raise AzureSearchError("missing Azure AI Search credential")
            headers["Authorization"] = f"Bearer {token.get_secret_value()}"
        return headers

    def _url(self, path: str) -> str:
        separator = "&" if "?" in path else "?"
        return (
            f"{self._config.endpoint}{path}{separator}"
            f"api-version={self._config.api_version}"
        )

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> AzureSearchClient:
        return self

    async def __aexit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        await self.close()

    async def create_or_update_index(self, *, vector_dimensions: int) -> None:
        schema = build_index_schema(
            index_name=self._config.index_name,
            vector_dimensions=vector_dimensions,
        )
        response = await self._client.put(
            self._url(f"/indexes/{self._config.index_name}"),
            headers=self._headers(),
            json=schema,
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            raise AzureSearchError(
                f"index update failed with status {response.status_code}"
            ) from error

    async def upload(
        self,
        documents: Sequence[SearchIndexDocument],
    ) -> None:
        if not documents:
            return
        payload = {
            "value": [
                {
                    "@search.action": "mergeOrUpload",
                    **document.model_dump(mode="json"),
                }
                for document in documents
            ]
        }
        response = await self._client.post(
            self._url(f"/indexes/{self._config.index_name}/docs/index"),
            headers=self._headers(),
            json=payload,
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            raise AzureSearchError(
                f"document upload failed with status {response.status_code}"
            ) from error

        result = response.json()
        failed = [
            item.get("key", "<unknown>")
            for item in result.get("value", [])
            if not item.get("status", False)
        ]
        if failed or len(result.get("value", [])) != len(documents):
            failed_keys = ", ".join(failed) or "incomplete response"
            raise AzureSearchError(f"document upload incomplete: {failed_keys}")

    async def hybrid_search(
        self,
        query: str,
        *,
        query_vector: Sequence[float],
        top_k: int = 5,
        filters: SearchFilters | None = None,
    ) -> tuple[AzureSearchHit, ...]:
        if not query.strip():
            raise ValueError("query must not be empty")
        if not query_vector:
            raise ValueError("query_vector must not be empty")
        if top_k < 1 or top_k > 50:
            raise ValueError("top_k must be between 1 and 50")

        payload = {
            "search": query,
            "top": top_k,
            "filter": build_odata_filter(filters or SearchFilters()),
            "select": ",".join(SearchIndexDocument.model_fields),
            "vectorQueries": [
                {
                    "kind": "vector",
                    "vector": list(query_vector),
                    "fields": "content_vector",
                    "k": max(top_k, 10),
                }
            ],
        }
        response = await self._client.post(
            self._url(f"/indexes/{self._config.index_name}/docs/search"),
            headers=self._headers(),
            json=payload,
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            raise AzureSearchError(
                f"hybrid search failed with status {response.status_code}"
            ) from error

        hits: list[AzureSearchHit] = []
        for raw_hit in response.json().get("value", []):
            document_payload = {
                field: raw_hit[field] for field in SearchIndexDocument.model_fields
            }
            hits.append(
                AzureSearchHit(
                    document=SearchIndexDocument.model_validate(document_payload),
                    score=float(raw_hit.get("@search.score", 0.0)),
                )
            )
        return tuple(hits)
