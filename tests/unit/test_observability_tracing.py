from __future__ import annotations

from decimal import Decimal

import pytest

from app.observability.costs import (
    ModelPricing,
    TokenUsage,
    estimate_usage_cost,
)
from app.observability.tracing import (
    InMemoryTracer,
    SpanToolTracer,
    ToolTrace,
)


def test_nested_span_contract_records_safe_metadata() -> None:
    tracer = InMemoryTracer()

    with tracer.start_span(
        "request", span_type="CHAIN", attributes={"correlation.id": "req-1"}
    ):
        with tracer.start_span(
            "graph.validate", span_type="CHAIN", attributes={"graph.node": "validate"}
        ):
            pass

    assert [span.name for span in tracer.spans] == ["graph.validate", "request"]
    assert tracer.spans[0].attributes == {"graph.node": "validate"}
    assert tracer.spans[1].attributes == {"correlation.id": "req-1"}


def test_tool_bridge_records_bounded_metadata_without_payload() -> None:
    tracer = InMemoryTracer()
    tool_tracer = SpanToolTracer(tracer)

    tool_tracer.record(
        ToolTrace(
            tool_name="read_sensor_data",
            status="succeeded",
            attempt_count=1,
            duration_ms=12.5,
        )
    )

    span = tracer.spans[0]
    assert span.name == "tool.read_sensor_data"
    assert span.span_type == "TOOL"
    assert span.attributes["tool.attempt_count"] == 1
    assert "payload" not in span.attributes


def test_span_records_failure_without_suppressing_business_error() -> None:
    tracer = InMemoryTracer()

    with pytest.raises(RuntimeError, match="operation failed"):
        with tracer.start_span("operation", span_type="CHAIN"):
            raise RuntimeError("operation failed")

    assert tracer.spans[0].status == "error"


def test_token_cost_uses_injected_pricing() -> None:
    usage = TokenUsage(
        input_tokens=1_000_000,
        cached_input_tokens=250_000,
        output_tokens=500_000,
    )
    pricing = ModelPricing(
        input_per_million=Decimal("2"),
        cached_input_per_million=Decimal("1"),
        output_per_million=Decimal("4"),
    )

    result = estimate_usage_cost(usage, pricing)

    assert usage.total_tokens == 1_500_000
    assert result.estimated_cost_usd == Decimal("3.75")


def test_invalid_token_usage_is_rejected() -> None:
    with pytest.raises(ValueError, match="cannot exceed"):
        TokenUsage(input_tokens=1, cached_input_tokens=2)
