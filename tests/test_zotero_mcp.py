import pytest

from nodes import retrieve as retrieve_module
from tools.contracts import ToolResult
from tools.mcp_zotero import build_zotero_mcp_tool
from tools.runtime import paper_tool_router, tool_registry
from tools.zotero_client import ZoteroReadOnlyClient


class FakeResponse:
    def __init__(self, payload, headers=None):
        self._payload = payload
        self.headers = headers or {}

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.pop(0)


def test_zotero_client_uses_versioned_get_and_keeps_key_out_of_url():
    session = FakeSession([
        FakeResponse([{
            "key": "ITEM1234",
            "data": {
                "itemType": "journalArticle",
                "title": "Agent Memory",
                "date": "2024",
                "creators": [{"firstName": "Ada", "lastName": "Lovelace"}],
                "tags": [{"tag": "agent"}],
                "collections": ["COLL1234"],
            },
        }], {"Total-Results": "1"}),
        FakeResponse([
            {"key": "NOTE1234", "data": {"itemType": "note", "note": "<p>关键结论</p>"}},
            {"key": "PDF12345", "data": {"itemType": "attachment", "contentType": "application/pdf"}},
        ]),
    ])
    client = ZoteroReadOnlyClient(
        base_url="https://api.zotero.org",
        library_type="user",
        library_id="42",
        api_key="secret-key",
        session=session,
    )

    result = client.search_items(query="memory", limit=1)

    assert result["items"][0]["authors"] == ["Ada Lovelace"]
    assert result["items"][0]["notes"] == ["关键结论"]
    assert result["items"][0]["pdf_attachment_keys"] == ["PDF12345"]
    assert all("secret-key" not in url for url, _ in session.calls)
    assert all(call[1]["headers"]["Zotero-API-Version"] == "3" for call in session.calls)
    assert all(call[1]["headers"]["Zotero-API-Key"] == "secret-key" for call in session.calls)


def test_zotero_client_requires_explicit_library_and_rejects_unknown_type():
    with pytest.raises(ValueError, match="ZOTERO_LIBRARY_ID"):
        ZoteroReadOnlyClient(base_url="https://api.zotero.org", library_type="user", library_id="")
    with pytest.raises(ValueError, match="user 或 group"):
        ZoteroReadOnlyClient(base_url="https://api.zotero.org", library_type="other", library_id="42")
    with pytest.raises(ValueError, match="数字 ID"):
        ZoteroReadOnlyClient(base_url="https://api.zotero.org", library_type="user", library_id="../42")


def test_zotero_mcp_tool_is_registered_read_only():
    tool = tool_registry.get("library.search.zotero.mcp")

    assert tool is not None
    assert tool.spec.risk_level.value == "read_only"
    assert tool.spec.capabilities == ("library.search",)
    assert paper_tool_router.resolve("library.search", "zotero") == tool.spec.name
    assert tool.audit_metadata["mcp_server"] == "paperagent-zotero"


def test_zotero_schema_rejects_path_like_collection_key():
    tool = build_zotero_mcp_tool()
    with pytest.raises(ValueError):
        tool.spec.input_model.model_validate({"collection_key": "../../secret"})


def test_main_retrieval_path_routes_zotero_items_to_documents(monkeypatch):
    monkeypatch.setattr(retrieve_module, "load_cached_papers", lambda *args, **kwargs: None)
    monkeypatch.setattr(retrieve_module, "save_cached_papers", lambda *args, **kwargs: None)
    monkeypatch.setattr(retrieve_module.settings, "RETRIEVAL_MODE", "zotero")
    monkeypatch.setattr(
        retrieve_module.paper_tool_executor,
        "execute",
        lambda tool_name, arguments: ToolResult(
            success=True,
            tool_name=tool_name,
            tool_version="1.0.0",
            source="zotero_mcp",
            data={
                "items": [{
                    "item_key": "ITEM1234",
                    "title": "Agent Memory",
                    "authors": ["Ada Lovelace"],
                    "year": 2024,
                    "abstract": "Memory architecture",
                    "tags": ["agent"],
                    "notes": ["重要笔记"],
                }],
                "total_matches": 1,
            },
            metadata={"tool_origin": "mcp", "mcp_server": "paperagent-zotero"},
        ),
    )

    result = retrieve_module.retrieve_by_query("agent memory", {})

    assert result["documents"][0]["entry_id"] == "ITEM1234"
    assert result["documents"][0]["source"] == "zotero"
    assert result["tool_executions"][0]["tool_route"]["capability"] == "library.search"
    assert result["tool_executions"][0]["tool_metadata"]["mcp_server"] == "paperagent-zotero"


def test_zotero_failure_stays_empty_instead_of_using_public_fallback(monkeypatch):
    monkeypatch.setattr(retrieve_module, "load_cached_papers", lambda *args, **kwargs: None)
    monkeypatch.setattr(retrieve_module.settings, "RETRIEVAL_MODE", "zotero")
    monkeypatch.setattr(
        retrieve_module.paper_tool_executor,
        "execute",
        lambda tool_name, arguments: ToolResult(
            success=False,
            tool_name=tool_name,
            source="zotero_mcp",
            error_code="EXECUTION_ERROR",
            error_message="缺少 ZOTERO_LIBRARY_ID",
        ),
    )

    result = retrieve_module.retrieve_by_query("my papers", {})

    assert result["documents"] == []
    assert result["retrieval_source"] == "zotero"
    assert "fallback_retriever" not in result["tools_used"]
    assert result["tool_executions"][0]["tool_error_code"] == "EXECUTION_ERROR"
