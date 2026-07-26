import nodes.retrieve as retrieve_module


def test_single_planned_query_uses_single_query_retrieval(monkeypatch):
    calls = []

    def fake_retrieve_by_query(query, state):
        calls.append(("single", query))
        return {
            "documents": [{"entry_id": "1"}],
            "retrieval_source": "cache",
            "retrieval_mode": "arxiv",
            "cache_hit": True,
            "tools_used": ["cache_retriever"],
        }

    def fail_multi_query(*args, **kwargs):
        raise AssertionError("single query must not use multi-query retrieval")

    monkeypatch.setattr(
        retrieve_module,
        "retrieve_by_query",
        fake_retrieve_by_query,
    )
    monkeypatch.setattr(
        retrieve_module,
        "retrieve_multi_query",
        fail_multi_query,
    )

    result = retrieve_module.retrieve_node(
        {
            "query": "什么是 RAG",
            "sub_queries": ["retrieval augmented generation"],
            "tools_used": [],
            "paper_metadata": {"query_complexity": "simple"},
        }
    )

    assert calls == [("single", "retrieval augmented generation")]
    assert result["paper_metadata"]["agentic_rag_enabled"] is False
    assert result["paper_metadata"]["retrieval_source"] == "cache"


def test_multiple_planned_queries_use_multi_query_retrieval(monkeypatch):
    calls = []

    def fake_multi_query(state, sub_queries):
        calls.append(("multi", sub_queries))
        return {
            "documents": [{"entry_id": "1"}, {"entry_id": "2"}],
            "paper_metadata": {"agentic_rag_enabled": True},
        }

    monkeypatch.setattr(
        retrieve_module,
        "retrieve_multi_query",
        fake_multi_query,
    )

    queries = ["RAG vs GraphRAG", "methods comparison"]
    result = retrieve_module.retrieve_node(
        {
            "query": "比较 RAG 和 GraphRAG",
            "sub_queries": queries,
            "tools_used": [],
        }
    )

    assert calls == [("multi", queries)]
    assert result["paper_metadata"]["agentic_rag_enabled"] is True
