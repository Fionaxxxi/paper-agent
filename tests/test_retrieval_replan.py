from nodes.retrieval_replan import build_retrieval_replan
import nodes.retrieve as retrieve_module


def test_replan_retries_same_query_for_transient_tool_failure():
    result = build_retrieval_replan({
        "query": "agent memory",
        "documents": [],
        "retrieval_score": 0.0,
        "retry_count": 0,
        "paper_metadata": {"search_query": "agent memory", "tool_executions": [{"tool_success": False, "tool_error_code": "TIMEOUT"}]},
    })

    assert result["retry_query"] == "agent memory"
    assert result["retrieval_replan"]["failure_type"] == "transient_tool_failure"
    assert result["retry_count"] == 1


def test_replan_broadens_empty_query_without_llm():
    result = build_retrieval_replan({"query": '"GraphRAG" (academic)', "documents": [], "retrieval_score": 0.0})

    assert result["retry_query"] == "GraphRAG academic research survey"
    assert result["retrieval_replan"]["action"] == "broaden_query"


def test_replan_expands_low_relevance_query_and_records_reason():
    result = build_retrieval_replan({"rewritten_query": "reflection agents", "documents": [{"title": "weak"}], "retrieval_score": 0.5})

    assert result["retry_query"] == "reflection agents survey review"
    assert result["retrieval_replan"]["failure_type"] == "low_relevance"
    assert "0.50" in result["retrieval_replan"]["reason"]


def test_retry_query_overrides_old_multi_query_plan(monkeypatch):
    calls = []
    monkeypatch.setattr(
        retrieve_module,
        "retrieve_by_query",
        lambda query, state: calls.append(query) or {
            "documents": [], "tools_used": [], "retrieval_mode": "arxiv",
            "tool_executions": [], "source_statuses": [],
        },
    )
    monkeypatch.setattr(
        retrieve_module,
        "retrieve_multi_query",
        lambda *args: (_ for _ in ()).throw(AssertionError("old plan must not rerun")),
    )

    retrieve_module.retrieve_node({"sub_queries": ["old one", "old two"], "retry_query": "broader query"})

    assert calls == ["broader query"]
