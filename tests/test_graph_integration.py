import pytest

import agent.graph as graph_module


@pytest.fixture
def instrumented_graph(monkeypatch):
    calls = []

    def node(name, result):
        def run(state):
            calls.append(name)
            return result(state) if callable(result) else result

        return run

    monkeypatch.setattr(
        graph_module,
        "query_rewrite_node",
        node("query_rewrite", lambda state: {"rewritten_query": state["query"]}),
    )
    monkeypatch.setattr(
        graph_module,
        "research_analyze_node",
        node("research_analyze", {"task_level": "L1"}),
    )
    monkeypatch.setattr(
        graph_module,
        "query_plan_node",
        node("query_plan", {"sub_queries": ["planned query"]}),
    )
    monkeypatch.setattr(
        graph_module,
        "retrieve_node",
        node("retrieve", {"documents": [{"title": "Local test paper"}]}),
    )
    monkeypatch.setattr(
        graph_module,
        "evaluate_node",
        node("evaluate", {"retrieval_score": 1.0}),
    )
    monkeypatch.setattr(
        graph_module,
        "reason_node",
        node("reason", {"task_type": "qa"}),
    )
    monkeypatch.setattr(
        graph_module,
        "generate_node",
        node("generate", {"answer": "grounded answer"}),
    )
    monkeypatch.setattr(
        graph_module,
        "metrics_node",
        node("metrics", {"token_usage": 0}),
    )
    monkeypatch.setattr(
        graph_module,
        "answer_verify_node",
        node(
            "answer_verify",
            {
                "answer_verification": {
                    "passed": True,
                    "should_reflect": False,
                }
            },
        ),
    )

    return graph_module.build_graph(), calls


def test_standard_query_runs_the_agentic_rag_path(instrumented_graph):
    graph, calls = instrumented_graph

    result = graph.invoke({"query": "graph rag", "retry_count": 0})

    assert calls == [
        "research_analyze",
        "query_rewrite",
        "query_plan",
        "retrieve",
        "evaluate",
        "reason",
        "generate",
        "answer_verify",
        "metrics",
    ]
    assert result["answer"] == "grounded answer"
    assert result["sub_queries"] == ["planned query"]


def test_pdf_query_skips_query_planning_and_retrieval(instrumented_graph):
    graph, calls = instrumented_graph

    result = graph.invoke(
        {"query": "summarize this PDF", "pdf_path": "paper.pdf", "retry_count": 0}
    )

    assert calls == ["research_analyze", "query_rewrite", "reason", "generate", "answer_verify", "metrics"]
    assert result["answer"] == "grounded answer"


def test_smalltalk_ends_before_all_rag_and_llm_nodes(instrumented_graph):
    graph, calls = instrumented_graph

    result = graph.invoke({"query": "hi", "retry_count": 0, "token_usage": 0})

    assert calls == []
    assert result["task_type"] == "smalltalk"
    assert result["answer"].startswith("你好")
    assert result["tools_used"] == []
    assert result["token_usage"] == 0
    assert result["paper_metadata"]["short_circuited"] is True
