"""Explicit allowlist for agent-visible tools."""

from collections.abc import Callable, Mapping
from typing import Any


class ToolRegistry:
    def __init__(self, tools: Mapping[str, Callable[..., Any]]) -> None:
        if not tools:
            raise ValueError("tool registry must not be empty")
        if any(not name or name.startswith("_") for name in tools):
            raise ValueError("tool names must be public and non-empty")
        self._tools = dict(tools)

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._tools))

    def get(self, name: str) -> Callable[..., Any]:
        try:
            return self._tools[name]
        except KeyError as exception:
            raise LookupError(f"tool is not allowed: {name}") from exception
