"""Default native tool runtime used by LangGraph nodes."""

from tools.arxiv_adapter import ArxivSearchTool
from tools.executor import ToolExecutor
from tools.openalex_adapter import OpenAlexSearchTool
from tools.registry import ToolRegistry
from tools.router import ToolRouter


def build_default_tool_runtime() -> tuple[ToolRegistry, ToolRouter, ToolExecutor]:
    registry = ToolRegistry()
    registry.register(ArxivSearchTool())
    registry.register(OpenAlexSearchTool())

    router = ToolRouter()
    router.register_route(
        capability="paper.search",
        source="arxiv",
        tool_name="paper.search.arxiv",
    )
    router.register_route(
        capability="paper.search",
        source="openalex",
        tool_name="paper.search.openalex",
    )

    return registry, router, ToolExecutor(registry)


tool_registry, paper_tool_router, paper_tool_executor = build_default_tool_runtime()
