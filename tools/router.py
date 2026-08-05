"""Deterministic capability-to-tool routing."""

from __future__ import annotations


class ToolRouter:
    def __init__(self) -> None:
        self._routes: dict[tuple[str, str], str] = {}

    def register_route(self, capability: str, source: str, tool_name: str) -> None:
        key = (capability, source)
        if key in self._routes:
            raise ValueError(f"tool route already registered: {capability}/{source}")
        self._routes[key] = tool_name

    def resolve(self, capability: str, source: str) -> str:
        try:
            return self._routes[(capability, source)]
        except KeyError as error:
            raise KeyError(f"no tool route for capability={capability}, source={source}") from error
