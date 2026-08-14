"""Default native tool runtime used by LangGraph nodes."""

from tools.arxiv_adapter import ArxivLookupTool, ArxivSearchTool
from tools.crossref_adapter import CrossrefLookupTool
from tools.executor import ToolExecutor
from tools.openalex_adapter import OpenAlexSearchTool
from tools.semantic_scholar_adapter import SemanticScholarLookupTool
from tools.mcp_paper_catalog import build_paper_catalog_mcp_tool
from tools.registry import ToolRegistry
from tools.router import ToolRouter


def build_default_tool_runtime() -> tuple[ToolRegistry, ToolRouter, ToolExecutor]:
    registry = ToolRegistry()
    registry.register(ArxivSearchTool())
    registry.register(ArxivLookupTool())
    registry.register(OpenAlexSearchTool())
    registry.register(CrossrefLookupTool())
    registry.register(SemanticScholarLookupTool())
    registry.register(build_paper_catalog_mcp_tool())

    router = ToolRouter()
    router.register_route(
        capability="paper.search",
        source="arxiv",
        tool_name="paper.search.arxiv",
    )
    router.register_route(
        capability="paper.lookup",
        source="crossref",
        tool_name="paper.lookup.crossref",
    )
    router.register_route(
        capability="paper.lookup",
        source="semantic_scholar",
        tool_name="paper.lookup.semantic_scholar",
    )
    router.register_route(
        capability="paper.lookup",
        source="arxiv",
        tool_name="paper.lookup.arxiv",
    )
    router.register_route(
        capability="paper.search",
        source="openalex",
        tool_name="paper.search.openalex",
    )
    router.register_route(
        capability="paper.catalog.search",
        source="mcp_catalog",
        tool_name="paper.catalog.search.mcp",
    )

    return registry, router, ToolExecutor(registry)


tool_registry, paper_tool_router, paper_tool_executor = build_default_tool_runtime()
