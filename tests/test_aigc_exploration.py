from nodes.query_plan import query_plan_node
from nodes.query_rewrite import query_rewrite_node
from research.analyzer import rule_analyze
from research.planning import build_l2_planner_lite, build_research_brief, validate_research_plan
from retrieval.research_query import normalized_research_topic
from retrieval.strategy import select_retrieval_strategy


QUERY = "aigc方面有什么可供参考"


def _planned_state():
    analysis = rule_analyze(QUERY)
    brief = build_research_brief(analysis)
    plan = build_l2_planner_lite(brief)
    return {
        "query": QUERY,
        "task_type": "recommend",
        "task_level": analysis.task_level,
        "research_analysis": analysis.model_dump(mode="python"),
        "research_plan": plan.model_dump(mode="python"),
        "research_plan_validation": validate_research_plan(
            plan, allowed_sources={*brief.allowed_sources, "retrieval_router", "evidence_store"}
        ).model_dump(mode="python"),
    }


def test_aigc_exploration_is_l2_multi_source_research_not_simple_qa():
    analysis = rule_analyze(QUERY)
    assert analysis.task_level == "L2"
    assert analysis.intent == "research_direction"
    assert analysis.requires_multiple_sources is True
    assert analysis.primary_skill == "research_direction"
    assert len(analysis.objectives) == 3


def test_aigc_term_is_expanded_before_academic_search():
    state = _planned_state()
    rewrite = query_rewrite_node(state)
    state.update(rewrite)
    topic = normalized_research_topic(state)
    assert "artificial intelligence generated content" in topic.casefold()
    assert "generative AI" in rewrite["rewritten_query"]
    assert "有什么可供参考" not in rewrite["rewritten_query"]


def test_aigc_exploration_builds_distinct_bounded_research_queries():
    state = _planned_state()
    state.update(query_rewrite_node(state))
    result = query_plan_node(state)
    queries = result["sub_queries"]
    assert len(queries) == 3
    assert len(set(queries)) == 3
    assert any("foundation models" in query for query in queries)
    assert any("text image video multimodal" in query for query in queries)
    assert any("safety detection watermarking" in query for query in queries)


def test_aigc_online_scope_uses_arxiv_and_openalex(monkeypatch):
    from retrieval import strategy
    monkeypatch.setattr(strategy.settings, "RETRIEVAL_MODE", "arxiv")
    state = _planned_state()
    state["retrieval_scope"] = "online"
    result = select_retrieval_strategy(state)
    assert result["sources"] == ["arxiv", "openalex"]
