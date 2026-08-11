"""Fail-open cache boundary; cache outages never fail core operations."""

from __future__ import annotations

from typing import Protocol


class AsyncCacheBackend(Protocol):
    async def get(self, key: str) -> bytes | None: ...

    async def set(self, key: str, value: bytes, *, ttl_seconds: int) -> None: ...


class FailOpenCache:
    """Treat backend errors as cache misses and ignored best-effort writes."""

    def __init__(self, backend: AsyncCacheBackend | None) -> None:
        self._backend = backend

    async def get(self, key: str) -> bytes | None:
        if self._backend is None:
            return None
        try:
            return await self._backend.get(key)
        except Exception:
            return None

    async def set(self, key: str, value: bytes, *, ttl_seconds: int) -> bool:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        if self._backend is None:
            return False
        try:
            await self._backend.set(key, value, ttl_seconds=ttl_seconds)
        except Exception:
            return False
        return True
