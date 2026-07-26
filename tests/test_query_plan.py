import pytest

from nodes.query_plan import (
    build_rule_based_sub_queries,
    classify_query_complexity,
    deduplicate_queries,
    query_plan_node,
)


def test_deduplicate_queries_preserves_order_and_ignores_case():
    queries = ["  Graph RAG  ", "graph rag", "", "Methods", "methods "]

    assert deduplicate_queries(queries) == ["Graph RAG", "Methods"]


@pytest.mark.parametrize(
    ("task_type", "expected_suffixes"),
    [
        ("qa", []),
        ("compare", ["methods comparison", "evaluation metrics", "limitations"]),
        ("summarize", ["survey overview", "methods", "contributions"]),
        ("recommend", ["open problems", "future research directions", "limitations challenges"]),
        ("citation", ["arxiv", "recent papers"]),
    ],
)
def test_build_rule_based_sub_queries_for_each_task_type(task_type, expected_suffixes):
    state = {
        "query": "original question",
        "rewritten_query": "graph rag",
        "task_type": task_type,
    }

    result = build_rule_based_sub_queries(state)

    assert result[0] == "graph rag"
    assert result[1:] == [f"graph rag {suffix}" for suffix in expected_suffixes]


def test_build_rule_based_sub_queries_falls_back_to_original_query():
    result = build_rule_based_sub_queries(
        {"query": "agentic rag", "rewritten_query": "", "task_type": "qa"}
    )

    assert result == ["agentic rag"]


@pytest.mark.parametrize(
    ("state", "expected_complexity"),
    [
        ({"query": "什么是 RAG", "task_type": "qa"}, "simple"),
        ({"query": "BERT 是哪一年发布的", "task_type": "qa"}, "simple"),
        ({"query": "比较 RAG 和 GraphRAG", "task_type": "qa"}, "complex"),
        ({"query": "recommend RAG research directions", "task_type": "qa"}, "complex"),
        ({"query": "plain query", "task_type": "compare"}, "complex"),
        ({"query": "hi", "task_type": "pdf_reading"}, "not_applicable"),
    ],
)
def test_classify_query_complexity_without_an_llm(state, expected_complexity):
    result = classify_query_complexity(state)

    assert result["query_complexity"] == expected_complexity
    assert result["complexity_reason"]


def test_query_plan_node_skips_pdf_reading_tasks():
    result = query_plan_node({"task_type": "pdf_reading"})

    assert result == {
        "sub_queries": [],
        "query_plan_enabled": False,
        "query_plan_reason": "pdf_reading task does not require retrieval planning",
        "query_complexity": "not_applicable",
        "complexity_reason": "pdf_reading skips external retrieval",
    }


def test_query_plan_node_preserves_and_extends_paper_metadata():
    result = query_plan_node(
        {
            "query": "RAG evaluation",
            "task_type": "qa",
            "paper_metadata": {"request_id": "req-1"},
        }
    )

    assert result["query_plan_enabled"] is True
    assert result["query_plan_reason"] == "single_query_for_simple_question"
    assert result["query_complexity"] == "simple"
    assert result["paper_metadata"]["request_id"] == "req-1"
    assert result["paper_metadata"]["sub_queries"] == result["sub_queries"]
    assert result["paper_metadata"]["sub_query_count"] == len(result["sub_queries"])
    assert result["paper_metadata"]["planned_query_count"] == 1
