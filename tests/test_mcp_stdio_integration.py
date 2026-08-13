from tools.mcp_paper_catalog import build_paper_catalog_mcp_tool
from tools.executor import ToolExecutor
from tools.registry import ToolRegistry


def _executor():
    registry=ToolRegistry();registry.register(build_paper_catalog_mcp_tool());return ToolExecutor(registry)


def test_real_stdio_mcp_server_returns_local_paper_catalog():
    result=_executor().execute("paper.catalog.search.mcp",{"query":"ReAct","limit":2})
    assert result.success is True
    assert result.data["papers"][0]["arxiv_id"] == "2210.03629"
    assert result.metadata["mcp_transport"] == "stdio"
    assert result.metadata["mcp_server"] == "paperagent-corpus"


def test_real_stdio_mcp_server_is_registered_in_default_runtime():
    from tools.runtime import tool_registry
    assert "paper.catalog.search.mcp" in tool_registry.list_names()
    assert tool_registry.get("paper.catalog.search.mcp").spec.risk_level.value == "read_only"
