import nodes.retrieve as retrieve_module
from nodes.evaluate import evaluate_node
from nodes.research_analyze import research_analyze_node
from nodes.research_schedule import research_schedule_node
from retrieval.strategy import select_retrieval_strategy


def test_l2_planner_lite_splits_two_methods_then_synthesizes():
    result = research_analyze_node({"query": "比较 ReAct 和 Reflexion 的核心机制"})
    tasks = result["research_plan"]["tasks"]

    assert result["task_level"] == "L2"
    assert [task["source"] for task in tasks] == ["retrieval_router", "retrieval_router", "evidence_store"]
    assert "ReAct" in tasks[0]["query"]
    assert "Reflexion" in tasks[1]["query"]
    assert tasks[2]["depends_on"] == ["T1", "T2"]
    assert result["research_plan_validation"]["valid"] is True


def test_l2_planner_lite_uses_bounded_schedule():
    analyzed = research_analyze_node({"query": "比较 ReAct 和 Reflexion 的核心机制"})
    scheduled = research_schedule_node(analyzed)["research_schedule"]

    assert scheduled["enabled"] is True
    assert scheduled["max_parallel_tasks"] == 2
    assert [len(wave["tasks"]) for wave in scheduled["waves"]] == [2, 1]
    assert scheduled["waves"][1]["tasks"][0]["task_kind"] == "synthesis"


def test_retrieval_router_distinguishes_online_hybrid_and_unavailable_personal(monkeypatch):
    monkeypatch.setattr(retrieve_module.settings, "RETRIEVAL_MODE", "arxiv")
    online = select_retrieval_strategy({"query": "查找2026年最新 Agent Memory 论文"})
    hybrid = select_retrieval_strategy({"query": "结合我的论文以及最新论文分析趋势"})
    personal = select_retrieval_strategy({"query": "根据我的收藏总结 Agent Memory"})

    assert online["mode"] == "online" and online["reason"] == "freshness_requested"
    assert hybrid["mode"] == "hybrid" and hybrid["sources"] == ["local_rag", "arxiv"]
    assert personal["requested_scope"] == "personal"
    assert personal["mode"] == "unavailable"
    assert personal["reason"] == "personal_library_not_configured"
    assert personal["fallback"] == "none"


def test_hybrid_strategy_merges_online_and_local_evidence(monkeypatch):
    monkeypatch.setattr(retrieve_module.settings, "RETRIEVAL_MODE", "arxiv")
    monkeypatch.setattr(
        retrieve_module, "retrieve_from_source",
        lambda query, state, source: {
            "papers": [{"title": "Online Paper", "summary": "fresh evidence", "source": "arxiv"}],
            "provider": source, "retrieval_source": source, "cache_hit": False,
            "tools_used": ["online"], "tool_execution": {},
        },
    )
    from local_rag import runtime
    monkeypatch.setattr(
        runtime, "search_local_papers",
        lambda query, limit: {"documents": [{"title": "Local Paper", "content": "private evidence", "source": "local_rag"}], "decision": {"route": "dense"}},
    )
    result = retrieve_module.retrieve_by_query("agent memory", {
        "retrieval_strategy": {"mode": "hybrid", "sources": ["local_rag", "arxiv"]}
    })

    assert result["retrieval_mode"] == "hybrid"
    assert {doc["source"] for doc in result["documents"]} == {"arxiv", "local_rag"}
    assert result["retrieval_source"] == "hybrid_local_online"


def test_local_scope_failure_falls_back_to_online(monkeypatch):
    monkeypatch.setattr(retrieve_module.settings, "RETRIEVAL_MODE", "arxiv")
    from local_rag import runtime
    monkeypatch.setattr(runtime, "search_local_papers", lambda *args: (_ for _ in ()).throw(RuntimeError("missing corpus")))
    monkeypatch.setattr(
        retrieve_module, "retrieve_from_source",
        lambda query, state, source: {
            "papers": [{"title": "Online Recovery", "summary": "evidence", "source": "arxiv"}],
            "provider": source, "retrieval_source": source, "cache_hit": False,
            "tools_used": ["online"], "tool_execution": {},
        },
    )
    result = retrieve_module.retrieve_by_query("本地知识库中的论文", {
        "retrieval_strategy": {"mode": "local", "sources": ["local_rag"], "fallback": "online"}
    })

    assert result["retrieval_mode"] == "arxiv"
    assert result["documents"][0]["title"] == "Online Recovery"


def test_unavailable_personal_scope_stops_without_public_fallback(monkeypatch):
    monkeypatch.setattr(retrieve_module.settings, "RETRIEVAL_MODE", "arxiv")
    strategy = select_retrieval_strategy({"query": "根据我的收藏总结 Agent Memory"})
    retrieved = retrieve_module.retrieve_by_query("Agent Memory", {
        "retrieval_strategy": strategy
    })
    evaluated = evaluate_node({
        "query": "根据我的收藏总结 Agent Memory",
        "retrieval_strategy": strategy,
        "documents": retrieved["documents"],
        "retry_count": 0,
    })

    assert retrieved["documents"] == []
    assert retrieved["retrieval_source"] == "requested_scope_unavailable"
    assert evaluated["retrieval_outcome"] == "stopped_low_quality"
    assert evaluated["retrieval_stop_reason"] == "requested_scope_unavailable"


def test_memory_scope_is_augmented_instead_of_reported_unavailable():
    strategy = select_retrieval_strategy({"query": "基于之前的结论继续检索 Agent Memory 论文"})
    assert strategy["mode"] == "online"
    assert strategy["requested_scope"] == "memory"
    assert strategy["reason"] == "memory_augmented_research"
