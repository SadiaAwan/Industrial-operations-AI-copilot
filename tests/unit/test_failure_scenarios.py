"""Cross-layer tests for the documented Phase 16 failure scenarios."""

import asyncio
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import CoreServices
from app.cache.redis import FailOpenCache
from app.main import create_app
from app.observability.tracing import ToolTrace
from app.resilience.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerPolicy,
)
from app.resilience.fallbacks import ServiceUnavailableError, call_with_fallback
from app.schemas.api import DependencyStatus
from app.schemas.tools import ToolErrorCode
from app.tools.runtime import RetryableToolError, ToolExecutor, ToolPolicy
from tests.api_fakes import fake_services


class FailingCacheBackend:
    async def get(self, key: str) -> bytes | None:
        raise ConnectionError(key)

    async def set(self, key: str, value: bytes, *, ttl_seconds: int) -> None:
        raise ConnectionError(key, value, ttl_seconds)


class FailingTracer:
    def record(self, trace: ToolTrace) -> None:
        raise RuntimeError(trace.tool_name)


class StaticReadiness:
    def __init__(self, dependencies: tuple[DependencyStatus, ...]) -> None:
        self._dependencies = dependencies

    async def check(self) -> tuple[DependencyStatus, ...]:
        return self._dependencies


def services_with_readiness(readiness: StaticReadiness) -> CoreServices:
    return replace(fake_services(), readiness=readiness)


def test_cache_outage_becomes_miss_and_does_not_block_core_flow() -> None:
    cache = FailOpenCache(FailingCacheBackend())

    assert asyncio.run(cache.get("machine:P-104")) is None
    assert (
        asyncio.run(cache.set("machine:P-104", b"safe", ttl_seconds=30))
        is False
    )


def test_primary_failure_uses_bounded_degraded_fallback() -> None:
    async def primary() -> str:
        raise ConnectionError("search unavailable")

    async def fallback() -> str:
        return "approved cached evidence"

    result = asyncio.run(call_with_fallback(primary, fallback))

    assert result.value == "approved cached evidence"
    assert result.degraded is True
    assert result.source == "fallback"


def test_double_failure_returns_safe_error_without_dependency_details() -> None:
    async def failing() -> str:
        raise ConnectionError("secret.internal.example")

    with pytest.raises(ServiceUnavailableError) as captured:
        asyncio.run(call_with_fallback(failing, failing))

    assert "secret.internal.example" not in str(captured.value)
    assert "retry later" in str(captured.value)


def test_observability_failure_does_not_change_tool_result() -> None:
    executor = ToolExecutor(tracer=FailingTracer())

    async def operation() -> str:
        return "diagnostic result"

    result = asyncio.run(executor.execute("sensor", operation))

    assert result.data == "diagnostic result"
    assert result.error is None


def test_open_circuit_returns_safe_dependency_error_without_calling_service() -> None:
    calls = 0
    breaker = CircuitBreaker(CircuitBreakerPolicy(failure_threshold=1))
    breaker.record_failure()
    executor = ToolExecutor(circuit_breaker=breaker)

    async def operation() -> str:
        nonlocal calls
        calls += 1
        return "unexpected"

    result = asyncio.run(executor.execute("maintenance", operation))

    assert calls == 0
    assert result.error is not None
    assert result.error.code is ToolErrorCode.DEPENDENCY_UNAVAILABLE


def test_tool_retries_finish_with_safe_error() -> None:
    attempts = 0

    async def no_sleep(delay: float) -> None:
        assert delay >= 0

    executor = ToolExecutor(
        policy=ToolPolicy(max_attempts=3), sleep=no_sleep
    )

    async def unavailable() -> str:
        nonlocal attempts
        attempts += 1
        raise RetryableToolError("private dependency detail")

    result = asyncio.run(executor.execute("incidents", unavailable))

    assert attempts == 3
    assert result.error is not None
    assert result.error.message == (
        "incidents dependency is temporarily unavailable"
    )


def test_optional_dependency_outage_keeps_application_ready() -> None:
    readiness = StaticReadiness(
        (
            DependencyStatus(name="database", status="ready"),
            DependencyStatus(
                name="cache", status="unavailable", required=False
            ),
            DependencyStatus(
                name="observability", status="degraded", required=False
            ),
        )
    )
    client = TestClient(create_app(services=services_with_readiness(readiness)))

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_critical_dependency_outage_fails_readiness_only() -> None:
    readiness = StaticReadiness(
        (DependencyStatus(name="database", status="unavailable"),)
    )
    client = TestClient(create_app(services=services_with_readiness(readiness)))

    assert client.get("/ready").status_code == 503
    assert client.get("/health").status_code == 200
