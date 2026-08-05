"""Default native tool runtime used by LangGraph nodes."""

from tools.arxiv_adapter import ArxivSearchTool
from tools.executor import ToolExecutor
from tools.registry import ToolRegistry
from tools.router import ToolRouter


def build_default_tool_runtime() -> tuple[ToolRegistry, ToolRouter, ToolExecutor]:
    registry = ToolRegistry()
    registry.register(ArxivSearchTool())

    router = ToolRouter()
    router.register_route(
        capability="paper.search",
        source="arxiv",
        tool_name="paper.search.arxiv",
    )

    return registry, router, ToolExecutor(registry)


tool_registry, paper_tool_router, paper_tool_executor = build_default_tool_runtime()
