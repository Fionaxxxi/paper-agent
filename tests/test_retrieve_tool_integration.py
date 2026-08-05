import nodes.retrieve as retrieve_module
from tools.contracts import ToolErrorCode, ToolResult


class FakeRouter:
    def __init__(self):
        self.calls = []

    def resolve(self, capability, source):
        self.calls.append((capability, source))
        return "paper.search.arxiv"


class FakeExecutor:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def execute(self, tool_name, arguments):
        self.calls.append((tool_name, arguments))
        return self.result


def test_cache_miss_uses_tool_runtime_and_records_execution(monkeypatch):
    router = FakeRouter()
    executor = FakeExecutor(
        ToolResult(
            success=True,
            tool_name="paper.search.arxiv",
            tool_version="1.0.0",
            source="arxiv",
            data={
                "papers": [
                    {
                        "title": "Unified Tool Layer",
                        "authors": ["Fiona"],
                        "year": 2026,
                        "summary": "Tool protocol test.",
                        "pdf_url": "https://example.com/tool.pdf",
                        "entry_id": "tool-1",
                        "source": "arxiv",
                    }
                ]
            },
            latency_seconds=0.12,
            attempt_count=1,
        )
    )
    saved = []
    monkeypatch.setattr(
        retrieve_module,
        "load_cached_papers",
        lambda query, source="": None,
    )
    monkeypatch.setattr(
        retrieve_module,
        "save_cached_papers",
        lambda query, papers, source="": saved.append((query, papers, source)),
    )
    monkeypatch.setattr(retrieve_module, "paper_tool_router", router)
    monkeypatch.setattr(retrieve_module, "paper_tool_executor", executor)

    result = retrieve_module.retrieve_by_query("tool agents", {"retry_count": 0})

    assert router.calls == [("paper.search", "arxiv")]
    assert executor.calls == [
        (
            "paper.search.arxiv",
            {"query": "tool agents", "max_results": 5},
        )
    ]
    assert result["retrieval_source"] == "arxiv"
    assert result["documents"][0]["entry_id"] == "tool-1"
    assert result["tool_execution"]["tool_success"] is True
    assert result["tool_execution"]["tool_latency_seconds"] == 0.12
    assert "paper.search.arxiv" in result["tools_used"]
    assert saved[0][0] == "tool agents"
    assert saved[0][2] == "arxiv"


def test_tool_failure_uses_existing_fallback_and_keeps_error_metadata(monkeypatch):
    router = FakeRouter()
    executor = FakeExecutor(
        ToolResult(
            success=False,
            tool_name="paper.search.arxiv",
            tool_version="1.0.0",
            source="arxiv",
            error_code=ToolErrorCode.TIMEOUT.value,
            error_message="timed out",
            latency_seconds=1.0,
            attempt_count=1,
        )
    )
    monkeypatch.setattr(
        retrieve_module,
        "load_cached_papers",
        lambda query, source="": None,
    )
    monkeypatch.setattr(retrieve_module, "paper_tool_router", router)
    monkeypatch.setattr(retrieve_module, "paper_tool_executor", executor)

    result = retrieve_module.retrieve_by_query("tool timeout", {"retry_count": 0})

    assert result["retrieval_source"] == "fallback"
    assert len(result["documents"]) == len(retrieve_module.FALLBACK_PAPERS)
    assert result["tool_execution"]["tool_success"] is False
    assert result["tool_execution"]["tool_error_code"] == ToolErrorCode.TIMEOUT.value
    assert "paper.search.arxiv" in result["tools_used"]
