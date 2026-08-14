from tools.mcp_paper_catalog import build_paper_catalog_mcp_tool
from tools.executor import ToolExecutor
from tools.registry import ToolRegistry
from nodes import retrieve as retrieve_module


def _executor():
    registry=ToolRegistry();registry.register(build_paper_catalog_mcp_tool());return ToolExecutor(registry)


def test_real_stdio_mcp_server_returns_local_paper_catalog():
    result=_executor().execute("paper.catalog.search.mcp",{"query":"ReAct","limit":2})
    assert result.success is True
    assert result.data["papers"][0]["arxiv_id"] == "2210.03629"
    assert result.metadata["mcp_transport"] == "stdio"
    assert result.metadata["mcp_server"] == "paperagent-corpus"


def test_real_stdio_mcp_server_is_registered_in_default_runtime():
    from tools.runtime import paper_tool_router, tool_registry
    assert "paper.catalog.search.mcp" in tool_registry.list_names()
    assert tool_registry.get("paper.catalog.search.mcp").spec.risk_level.value == "read_only"
    assert paper_tool_router.resolve("paper.catalog.search", "mcp_catalog") == "paper.catalog.search.mcp"


def test_main_retrieval_path_can_explicitly_route_to_mcp(monkeypatch):
    monkeypatch.setattr(retrieve_module, "load_cached_papers", lambda *args, **kwargs: None)
    monkeypatch.setattr(retrieve_module, "save_cached_papers", lambda *args, **kwargs: None)
    monkeypatch.setattr(retrieve_module.settings, "RETRIEVAL_MODE", "mcp_catalog")

    result = retrieve_module.retrieve_by_query("ReAct", {})

    assert result["documents"][0]["entry_id"] == "2210.03629"
    assert result["documents"][0]["source"] == "mcp_catalog"
    execution = result["tool_executions"][0]
    assert execution["tool_route"]["capability"] == "paper.catalog.search"
    assert execution["tool_metadata"]["tool_origin"] == "mcp"
    assert execution["tool_metadata"]["mcp_server"] == "paperagent-corpus"
