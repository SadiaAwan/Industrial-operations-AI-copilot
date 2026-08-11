# Failure handling and resilience

Phase 16 applies bounded failure handling at dependency boundaries. Retries are
never used for validation, authorization, or other permanent errors. Business
operations must remain safe when cache or observability services fail.

## Runtime rules

- Every external attempt has a timeout and a finite attempt limit.
- Backoff grows exponentially and is capped; retry loops have no unbounded path.
- Repeated dependency failures open a circuit. After the recovery interval, one
  half-open probe decides whether the circuit closes or reopens.
- Cancellation propagates immediately and is never converted into a retry.
- A fallback has its own shorter timeout and returns explicit degraded metadata.
- When both primary and fallback fail, callers receive a stable message without
  internal hostnames, credentials, payloads, or exception text.
- Cache reads fail open as misses and cache writes are best effort.
- Tracing and metrics errors are ignored at the observability boundary.

## Readiness policy

Liveness only confirms that the process is running. Readiness distinguishes
required dependencies from optional accelerators:

| Dependency class | Example | Outage behaviour | `/ready` |
| --- | --- | --- | --- |
| Required | PostgreSQL, active model/search provider | Stop accepting dependent work safely | `503` |
| Optional | Cache, tracing, metrics backend | Continue in degraded mode | `200` |

An optional dependency may report `degraded` or `unavailable`; both remain
visible in the response so operations can alert without removing healthy API
instances from service.

## Verified failure scenarios

1. Slow calls time out and stop at the configured maximum attempt count.
2. Backoff is capped even when multiple attempts fail.
3. An open circuit prevents calls until its recovery window elapses.
4. A recovered half-open probe closes the circuit; another failure reopens it.
5. Primary service failure selects a separately bounded fallback.
6. Primary and fallback failure produce a sanitized unavailable response.
7. Cache outage behaves as a miss and never blocks the core flow.
8. Tracing failure cannot change a successful tool result.
9. Optional cache or observability outages retain readiness.
10. Required database outage fails readiness while liveness remains healthy.

These scenarios are merge-blocking in `tests/unit/test_resilience_policy.py`,
`tests/unit/test_circuit_breaker.py`, and
`tests/unit/test_failure_scenarios.py`.
