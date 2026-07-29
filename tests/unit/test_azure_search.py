"""Tests for the Azure AI Search REST adapter."""

import asyncio
import json
from datetime import date
from typing import Any

import httpx
import pytest
from pydantic import ValidationError

from app.retrieval.azure_search import (
    AzureSearchClient,
    AzureSearchConfig,
    build_index_schema,
)
from app.retrieval.hybrid_search import SearchFilters
from app.retrieval.indexing import SearchIndexDocument


def _document() -> SearchIndexDocument:
    return SearchIndexDocument(
        chunk_id="manual-abc",
        document_id="pump_maintenance_manual_v2",
        title="Centrifugal Pump Maintenance Manual",
        section="7.3 Bearing vibration and temperature",
        machine_type="centrifugal_pump",
        document_type="manual",
        revision="2.1",
        status="approved",
        effective_date="2026-01-10",
        source_path="manuals/maintenance.md",
        content="Bearing vibration and temperature evidence.",
        content_vector=(0.5, 0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
        embedding_model="test-embedding",
    )


def _config() -> AzureSearchConfig:
    return AzureSearchConfig(
        endpoint="https://example.search.windows.net/",
        index_name="pump-documents",
        api_key="secret-test-key",
    )


def test_config_requires_https_and_exactly_one_credential() -> None:
    with pytest.raises(ValidationError, match="HTTPS"):
        AzureSearchConfig(
            endpoint="http://example.test",
            index_name="pump-documents",
            api_key="key",
        )
    with pytest.raises(ValidationError, match="exactly one"):
        AzureSearchConfig(
            endpoint="https://example.test",
            index_name="pump-documents",
        )


def test_index_schema_configures_hybrid_vector_fields() -> None:
    schema = build_index_schema(
        index_name="pump-documents",
        vector_dimensions=128,
    )
    fields = {field["name"]: field for field in schema["fields"]}

    assert fields["chunk_id"]["key"] is True
    assert fields["content"]["searchable"] is True
    assert fields["content_vector"]["dimensions"] == 128
    assert fields["content_vector"]["vectorSearchProfile"] == "default-vector-profile"


def test_create_index_and_upload_send_expected_payloads() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "PUT":
            return httpx.Response(201, json={"name": "pump-documents"})
        return httpx.Response(
            200,
            json={
                "value": [
                    {
                        "key": "manual-abc",
                        "status": True,
                        "statusCode": 200,
                    }
                ]
            },
        )

    async def exercise() -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler)
        ) as http_client:
            client = AzureSearchClient(_config(), client=http_client)
            await client.create_or_update_index(vector_dimensions=8)
            await client.upload([_document()])

    asyncio.run(exercise())

    assert [request.method for request in requests] == ["PUT", "POST"]
    assert requests[0].headers["api-key"] == "secret-test-key"
    upload_payload: dict[str, Any] = json.loads(requests[1].content)
    assert upload_payload["value"][0]["@search.action"] == "mergeOrUpload"
    assert upload_payload["value"][0]["chunk_id"] == "manual-abc"


def test_hybrid_search_builds_safe_filters_and_parses_hits() -> None:
    captured_payload: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_payload.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "value": [
                    {
                        **_document().model_dump(mode="json"),
                        "@search.score": 0.91,
                    }
                ]
            },
        )

    async def exercise() -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler)
        ) as http_client:
            client = AzureSearchClient(_config(), client=http_client)
            hits = await client.hybrid_search(
                "bearing vibration",
                query_vector=(1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
                filters=SearchFilters(
                    machine_type="centrifugal_pump",
                    document_types=("manual",),
                    effective_on=date(2026, 7, 29),
                ),
            )
            assert hits[0].document.chunk_id == "manual-abc"
            assert hits[0].score == pytest.approx(0.91)

    asyncio.run(exercise())

    assert captured_payload["search"] == "bearing vibration"
    assert captured_payload["vectorQueries"][0]["fields"] == "content_vector"
    assert "status eq 'approved'" in captured_payload["filter"]
    assert "machine_type eq 'centrifugal_pump'" in captured_payload["filter"]
    assert "search.in(document_type, 'manual', ',')" in captured_payload["filter"]
