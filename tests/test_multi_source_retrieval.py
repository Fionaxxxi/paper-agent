import nodes.retrieve as retrieve_module
from tools.contracts import ToolErrorCode, ToolResult


class SourceRouter:
    def __init__(self):
        self.calls = []

    def resolve(self, capability, source):
        self.calls.append((capability, source))
        return f"paper.search.{source}"


class SourceExecutor:
    def __init__(self, results):
        self.results = results
        self.calls = []

    def execute(self, tool_name, arguments):
        self.calls.append((tool_name, arguments))
        return self.results[tool_name]


def paper(title, source, entry_id, doi=""):
    return {
        "title": title,
        "authors": ["Fiona"],
        "year": 2026,
        "summary": f"{source} result",
        "pdf_url": "",
        "entry_id": entry_id,
        "doi": doi,
        "source": source,
    }


def success(tool_name, source, papers):
    return ToolResult(
        success=True,
        tool_name=tool_name,
        tool_version="1.0.0",
        source=source,
        data={"papers": papers},
        latency_seconds=0.1,
        attempt_count=1,
    )


def configure_multi_source(monkeypatch, results):
    router = SourceRouter()
    executor = SourceExecutor(results)
    monkeypatch.setattr(retrieve_module.settings, "RETRIEVAL_MODE", "multi")
    monkeypatch.setattr(
        retrieve_module.settings,
        "MULTI_SOURCE_PROVIDERS",
        "arxiv,openalex",
    )
    monkeypatch.setattr(
        retrieve_module,
        "load_cached_papers",
        lambda query, source="": None,
    )
    monkeypatch.setattr(
        retrieve_module,
        "save_cached_papers",
        lambda query, papers, source="": None,
    )
    monkeypatch.setattr(retrieve_module, "paper_tool_router", router)
    monkeypatch.setattr(retrieve_module, "paper_tool_executor", executor)
    return router, executor


def test_multi_source_retrieval_calls_both_tools_and_deduplicates_by_doi(monkeypatch):
    shared_doi = "https://doi.org/10.1000/shared"
    results = {
        "paper.search.arxiv": success(
            "paper.search.arxiv",
            "arxiv",
            [paper("Shared Paper", "arxiv", "2401.1", shared_doi)],
        ),
        "paper.search.openalex": success(
            "paper.search.openalex",
            "openalex",
            [
                paper("Shared Paper", "openalex", "W1", "10.1000/SHARED"),
                paper("OpenAlex Only", "openalex", "W2", "10.1000/unique"),
            ],
        ),
    }
    router, executor = configure_multi_source(monkeypatch, results)

    result = retrieve_module.retrieve_by_query("research agents", {"retry_count": 0})

    assert router.calls == [
        ("paper.search", "arxiv"),
        ("paper.search", "openalex"),
    ]
    assert [call[0] for call in executor.calls] == [
        "paper.search.arxiv",
        "paper.search.openalex",
    ]
    assert result["retrieval_source"] == "multi_source"
    assert [document["title"] for document in result["documents"]] == [
        "Shared Paper",
        "OpenAlex Only",
    ]
    assert result["raw_document_count"] == 3
    assert result["deduplicated_count"] == 1
    assert len(result["tool_executions"]) == 2


def test_multi_source_retrieval_keeps_success_when_one_provider_fails(monkeypatch):
    results = {
        "paper.search.arxiv": ToolResult(
            success=False,
            tool_name="paper.search.arxiv",
            source="arxiv",
            error_code=ToolErrorCode.TIMEOUT.value,
            error_message="timed out",
            latency_seconds=1.0,
            attempt_count=1,
        ),
        "paper.search.openalex": success(
            "paper.search.openalex",
            "openalex",
            [paper("Available Work", "openalex", "W3")],
        ),
    }
    configure_multi_source(monkeypatch, results)

    result = retrieve_module.retrieve_by_query("partial failure", {"retry_count": 0})

    assert result["retrieval_source"] == "multi_source"
    assert [document["title"] for document in result["documents"]] == [
        "Available Work"
    ]
    assert result["tool_executions"][0]["tool_error_code"] == "TIMEOUT"
    assert "fallback_retriever" not in result["tools_used"]
