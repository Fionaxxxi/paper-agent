"""Registration and discovery for native and future MCP tools."""

from __future__ import annotations

from tools.base import Tool


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        name = tool.spec.name
        if name in self._tools:
            raise ValueError(f"tool already registered: {name}")
        self._tools[name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list_names(self) -> list[str]:
        return sorted(self._tools)

    def list_by_capability(self, capability: str) -> list[Tool]:
        return [
            self._tools[name]
            for name in self.list_names()
            if capability in self._tools[name].spec.capabilities
        ]
