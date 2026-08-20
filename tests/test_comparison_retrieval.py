import nodes.retrieve as retrieve_module
from nodes.evaluate import evaluate_node
from nodes.query_rewrite import query_rewrite_node
from nodes.retrieval_replan import build_retrieval_replan


QUERY = "比较 GraphRAG 和 LightRAG 的核心设计"


def test_comparison_query_rewrite_preserves_both_entities_and_design_scope():
    result = query_rewrite_node({"query": QUERY, "task_type": "compare"})

    assert "GraphRAG" in result["rewritten_query"]
    assert "LightRAG" in result["rewritten_query"]
    assert "architecture design comparison" in result["rewritten_query"]
    assert result["paper_metadata"]["query_entities"] == ["GraphRAG", "LightRAG"]


def test_comparison_evaluator_requires_both_entities_and_explains_missing_side():
    one_side = evaluate_node({
        "query": QUERY,
        "task_type": "compare",
        "documents": [{"title": "GraphRAG", "content": "community summaries"}],
        "retry_count": 0,
    })
    both_sides = evaluate_node({
        "query": QUERY,
        "task_type": "compare",
        "documents": [
            {"title": "GraphRAG", "content": "community summaries"},
            {"title": "LightRAG", "content": "dual-level retrieval"},
        ],
        "retry_count": 0,
    })

    assert one_side["retrieval_score"] == 0.55
    assert one_side["retrieval_evaluation"]["failure_type"] == "source_coverage_missing"
    assert one_side["retrieval_evaluation"]["comparison_coverage"]["missing_entities"] == ["LightRAG"]
    assert both_sides["retrieval_score"] == 0.85
    assert both_sides["retrieval_outcome"] == "accepted"


def test_online_comparison_uses_local_fallback_only_for_missing_entity(monkeypatch):
    monkeypatch.setattr(retrieve_module.settings, "RETRIEVAL_MODE", "arxiv")
    monkeypatch.setattr(retrieve_module.settings, "COMPARISON_LOCAL_FALLBACK_ENABLED", True)
    calls = []

    from local_rag import runtime

    def fake_local(query, limit):
        calls.append((query, limit))
        return {
            "documents": [{"title": "LightRAG: Simple and Fast Retrieval-Augmented Generation", "content": "dual-level retrieval and incremental update", "source": "local_rag"}],
            "decision": {"route": "dense"},
        }

    monkeypatch.setattr(runtime, "search_local_papers", fake_local)
    documents, coverage, tools, statuses = retrieve_module.supplement_comparison_from_local(
        [{"title": "From Local to Global: A Graph RAG Approach", "content": "community summaries", "source": "arxiv"}],
        {"query": QUERY, "task_type": "compare"},
    )

    assert calls == [("LightRAG architecture method retrieval design", 3)]
    assert coverage["passed"] is True
    assert coverage["fallback_status"] == "recovered"
    assert {row["source"] for row in documents} == {"arxiv", "local_rag"}
    assert "local_rag_retriever" in tools
    assert statuses[0]["search_entity"] == "LightRAG"


def test_missing_comparison_side_gets_targeted_single_replan():
    result = build_retrieval_replan({
        "query": QUERY,
        "documents": [{"title": "GraphRAG"}],
        "retrieval_score": 0.55,
        "retrieval_evaluation": {
            "failure_type": "source_coverage_missing",
            "comparison_coverage": {"missing_entities": ["LightRAG"]},
        },
        "retry_count": 0,
    })

    assert result["retrieval_replan"]["failure_type"] == "source_coverage_missing"
    assert result["retrieval_replan"]["action"] == "target_missing_comparison_entity"
    assert result["retry_query"] == "LightRAG architecture method original paper"
