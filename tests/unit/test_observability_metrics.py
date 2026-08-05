from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.observability.metrics import (
    MetricRegistry,
    MetricsToolTracer,
    ObservabilityMetrics,
)
from app.observability.tracing import InMemoryTracer, ToolTrace


def test_registry_renders_counters_and_histograms() -> None:
    registry = MetricRegistry()
    registry.increment("requests_total", labels={"status": "ok"})
    registry.observe("latency_seconds", 0.2, labels={"route": "/chat"})

    output = registry.render_prometheus()

    assert 'requests_total{status="ok"} 1' in output
    assert 'latency_seconds_bucket{route="/chat",le="0.25"} 1' in output
    assert 'latency_seconds_count{route="/chat"} 1' in output


def test_tool_metrics_include_retry_and_timeout() -> None:
    metrics = ObservabilityMetrics()
    tracer = MetricsToolTracer(metrics)
    tracer.record(
        ToolTrace(
            tool_name="sensor",
            status="failed",
            attempt_count=2,
            duration_ms=250,
            error_code="timeout",
        )
    )

    output = metrics.registry.render_prometheus()

    assert 'copilot_tool_calls_total{status="failed",tool="sensor"} 1' in output
    assert 'copilot_tool_retries_total{tool="sensor"} 1' in output
    assert 'copilot_tool_timeouts_total{tool="sensor"} 1' in output


def test_request_is_traced_measured_and_exposed_end_to_end() -> None:
    tracer = InMemoryTracer()
    metrics = ObservabilityMetrics()
    client = TestClient(create_app(tracer=tracer, metrics=metrics))

    response = client.get("/health", headers={"X-Correlation-ID": "req-e2e"})
    exposition = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["X-Correlation-ID"] == "req-e2e"
    assert tracer.spans[0].name == "http.request"
    assert tracer.spans[0].attributes["correlation.id"] == "req-e2e"
    assert tracer.spans[0].attributes["http.route"] == "/health"
    assert "copilot_http_requests_total" in exposition.text


def test_grafana_dashboard_references_declared_metrics() -> None:
    dashboard_path = Path("dashboards/grafana/dashboard.json")
    dashboard = json.loads(dashboard_path.read_text(encoding="utf-8"))
    expressions = " ".join(
        target["expr"]
        for panel in dashboard["panels"]
        for target in panel.get("targets", [])
    )

    assert dashboard["uid"] == "industrial-operations-copilot"
    assert "copilot_http_request_duration_seconds_bucket" in expressions
    assert "copilot_tool_timeouts_total" in expressions
    assert "copilot_estimated_cost_usd_total" in expressions
