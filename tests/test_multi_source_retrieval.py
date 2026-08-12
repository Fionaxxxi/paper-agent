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


def test_multi_source_retrieval_uses_reranker_only_when_feature_flag_is_enabled(
    monkeypatch,
):
    results = {
        "paper.search.arxiv": success(
            "paper.search.arxiv",
            "arxiv",
            [paper("Unrelated Work", "arxiv", "A1")],
        ),
        "paper.search.openalex": success(
            "paper.search.openalex",
            "openalex",
            [paper("Reflexion Language Agents", "openalex", "O1")],
        ),
    }
    configure_multi_source(monkeypatch, results)
    monkeypatch.setattr(retrieve_module.settings, "MULTI_SOURCE_RERANK_ENABLED", True)

    result = retrieve_module.retrieve_by_query("reflexion language agents", {})

    assert result["documents"][0]["source"] == "openalex"
    assert result["ranking_strategy"] == "deterministic_cross_source_v1"
    assert result["candidate_count_before_top_k"] == 2


def test_multi_source_metadata_verification_can_quarantine_unsafe_record(
    monkeypatch,
):
    results = {
        "paper.search.arxiv": success(
            "paper.search.arxiv",
            "arxiv",
            [paper("Chain of Thought Reasoning", "arxiv", "safe")],
        ),
        "paper.search.openalex": success(
            "paper.search.openalex",
            "openalex",
            [
                paper(
                    "Unrelated Metadata Record",
                    "openalex",
                    "https://openalex.org/W1",
                    "https://doi.org/10.48550/arxiv.2201.11903",
                )
            ],
        ),
    }
    configure_multi_source(monkeypatch, results)
    monkeypatch.setattr(retrieve_module.settings, "MULTI_SOURCE_RERANK_ENABLED", True)
    monkeypatch.setattr(
        retrieve_module.settings,
        "MULTI_SOURCE_METADATA_VERIFICATION_ENABLED",
        True,
    )

    result = retrieve_module.retrieve_by_query("chain of thought reasoning", {})

    assert [item["entry_id"] for item in result["documents"]] == ["safe"]
    assert result["ranking_strategy"] == "deterministic_cross_source_verified_v2"
    assert result["metadata_quarantined_count"] == 1


def test_arxiv_authority_switch_is_independent_from_legacy_metadata_gate(monkeypatch):
    results = {
        "paper.search.arxiv": success("paper.search.arxiv", "arxiv", []),
        "paper.search.openalex": success(
            "paper.search.openalex",
            "openalex",
            [paper("Wrong Secondary Title", "openalex", "W1", "10.48550/arxiv.2205.11916")],
        ),
    }
    configure_multi_source(monkeypatch, results)
    monkeypatch.setattr(retrieve_module.settings, "MULTI_SOURCE_RERANK_ENABLED", True)
    monkeypatch.setattr(retrieve_module.settings, "MULTI_SOURCE_METADATA_VERIFICATION_ENABLED", False)
    monkeypatch.setattr(retrieve_module.settings, "ARXIV_AUTHORITY_VERIFICATION_ENABLED", True)
    monkeypatch.setattr(
        retrieve_module,
        "load_arxiv_authority_evidence",
        lambda groups: (
            {"arxiv:2205.11916": paper("Large Language Models are Zero-Shot Reasoners", "arxiv", "https://arxiv.org/abs/2205.11916")},
            [],
            ["paper.lookup.arxiv"],
        ),
    )

    result = retrieve_module.retrieve_by_query("zero shot reasoning", {})

    assert result["ranking_strategy"] == "canonical_authority_verified_v3"
    assert result["documents"][0]["title"] == "Large Language Models are Zero-Shot Reasoners"
    assert "paper.lookup.arxiv" in result["tools_used"]
