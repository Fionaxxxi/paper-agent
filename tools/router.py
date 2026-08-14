"""Deterministic capability-to-tool routing."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ToolRouteDecision:
    """可写入 Agent 轨迹的确定性工具路由结果。"""

    capability: str
    source: str
    tool_name: str


class ToolRouter:
    def __init__(self) -> None:
        self._routes: dict[tuple[str, str], str] = {}

    def register_route(self, capability: str, source: str, tool_name: str) -> None:
        key = (capability, source)
        if key in self._routes:
            raise ValueError(f"tool route already registered: {capability}/{source}")
        self._routes[key] = tool_name

    def resolve(self, capability: str, source: str) -> str:
        return self.select(capability, source).tool_name

    def select(self, capability: str, source: str) -> ToolRouteDecision:
        try:
            tool_name = self._routes[(capability, source)]
        except KeyError as error:
            raise KeyError(f"no tool route for capability={capability}, source={source}") from error
        return ToolRouteDecision(
            capability=capability,
            source=source,
            tool_name=tool_name,
        )
