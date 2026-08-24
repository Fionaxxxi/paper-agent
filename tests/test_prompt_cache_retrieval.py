from types import SimpleNamespace

import nodes.retrieve as retrieve_module
from nodes.evaluate import evaluate_node
from nodes.query_plan import query_plan_node
from nodes.query_rewrite import query_rewrite_node
from research.analyzer import rule_analyze
from research.planning import build_l2_planner_lite, build_research_brief, validate_research_plan
from retrieval.strategy import select_retrieval_strategy


QUERY = "agent中的prompt cache是什么，怎么用"


def _state():
    analysis = rule_analyze(QUERY)
    brief = build_research_brief(analysis)
    plan = build_l2_planner_lite(brief)
    state = {
        "query": QUERY, "task_type": "qa", "task_level": analysis.task_level,
        "research_analysis": analysis.model_dump(mode="python"),
        "research_plan": plan.model_dump(mode="python"),
        "research_plan_validation": validate_research_plan(
            plan, allowed_sources={*brief.allowed_sources, "retrieval_router", "evidence_store"}
        ).model_dump(mode="python"),
    }
    state.update(query_rewrite_node(state))
    return state


def test_prompt_cache_term_beats_generic_agent_rewrite_and_uses_l2():
    state = _state()
    assert state["task_level"] == "L2"
    assert state["research_analysis"]["requires_multiple_sources"] is True
    assert state["research_analysis"]["complexity_decision_basis"] == "prompt_cache_policy_l2"
    assert "prompt caching" in state["rewritten_query"].casefold()
    assert "automatic prefix caching" in state["rewritten_query"].casefold()


def test_prompt_cache_plan_builds_concept_mechanism_and_agent_queries():
    queries = query_plan_node(_state())["sub_queries"]
    assert len(queries) == 3 and len(set(queries)) == 3
    assert any(all(term in query for term in ("prompt caching", "survey", "benchmarks")) for query in queries)
    assert any(all(term in query for term in ("radix tree", "KV cache")) for query in queries)
    assert any(all(term in query for term in ("agent", "context engineering", "cost optimization")) for query in queries)


def test_prompt_cache_online_scope_uses_arxiv_and_openalex(monkeypatch):
    from retrieval import strategy
    monkeypatch.setattr(strategy.settings, "RETRIEVAL_MODE", "arxiv")
    result = select_retrieval_strategy({**_state(), "retrieval_scope": "online"})
    assert result["sources"] == ["arxiv", "openalex"]


def test_generic_agent_cache_is_rejected_and_provider_is_called(monkeypatch):
    stale = [{"title": "Agent Planning", "summary": "Agents use planning and memory."}]
    fresh = [{"title": "Prompt Cache", "summary": "Prompt caching reuses a shared prefix."}]
    monkeypatch.setattr(retrieve_module, "load_cached_papers", lambda query, source: stale)
    monkeypatch.setattr(retrieve_module, "save_cached_papers", lambda *args, **kwargs: None)
    monkeypatch.setattr(retrieve_module.paper_tool_router, "resolve", lambda capability, source: "fake.search")
    result_object = SimpleNamespace(
        success=True, data={"papers": fresh}, tool_name="fake.search", tool_version="1",
        error_code="", error_message="", latency_seconds=0.01, attempt_count=1,
        source="arxiv", metadata={},
    )
    monkeypatch.setattr(retrieve_module.paper_tool_executor, "execute", lambda **kwargs: result_object)

    result = retrieve_module.retrieve_from_source(
        _state()["rewritten_query"], _state(), "arxiv"
    )

    assert result["cache_hit"] is False
    assert result["retrieval_source"] == "arxiv"
    assert result["cache_rejection"] == "topic_coverage_missing:prompt_cache"
    assert result["papers"] == fresh


def test_generic_agent_documents_cannot_pass_prompt_cache_quality_gate():
    result = evaluate_node({
        **_state(),
        "documents": [
            {"title": "Learning to Plan", "content": "LLM agent planning and memory"},
            {"title": "Tool Learning", "content": "Agents learn to call tools"},
        ],
    })
    assert result["retrieval_score"] < 0.7
    assert result["retrieval_evaluation"]["failure_type"] == "topic_coverage_missing"


def test_real_prompt_or_prefix_cache_evidence_can_pass_quality_gate():
    result = evaluate_node({
        **_state(),
        "documents": [
            {"title": "Automatic Prefix Caching", "content": "Prompt caching reuses shared prefixes in LLM serving."},
            {"title": "Prompt Cache for Agents", "content": "Agent systems reduce latency with context caching."},
            {"title": "Efficient LLM Serving", "content": "Prefix caching and KV cache improve inference."},
        ],
    })
    assert result["retrieval_score"] >= 0.7
    assert result["retrieval_evaluation"]["topic_coverage"]["passed"] is True
