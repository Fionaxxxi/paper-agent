from nodes.evaluate import evaluate_node, rule_based_score
from nodes.query_plan import query_plan_node
from nodes.query_rewrite import query_rewrite_node
from nodes.retrieval_replan import build_retrieval_replan
from research.analyzer import rule_analyze
from research.planning import build_l2_planner_lite, build_research_brief, validate_research_plan
from retrieval.strategy import select_retrieval_strategy


QUERY = "harness工程如何赋能agent开发，和workflow有什么关系"


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


def test_harness_engineering_is_l2_multi_source_and_preserves_core_terms():
    state = _state()
    analysis = state["research_analysis"]
    assert analysis["task_level"] == "L2"
    assert analysis["requires_multiple_sources"] is True
    assert analysis["complexity_decision_basis"] == "harness_engineering_policy_l2"
    assert all(term in state["rewritten_query"].casefold() for term in ("harness", "workflow", "orchestration"))


def test_harness_plan_builds_runtime_workflow_and_governance_queries():
    result = query_plan_node(_state())
    queries = result["sub_queries"]
    assert len(queries) == 3 and len(set(queries)) == 3
    assert any("scaffolding runtime infrastructure" in query for query in queries)
    assert any(all(term in query for term in ("workflow", "orchestration", "state machine")) for query in queries)
    assert any(all(term in query for term in ("tool sandbox", "observability")) for query in queries)


def test_generic_agent_papers_cannot_pass_harness_topic_coverage():
    state = {
        **_state(),
        "documents": [
            {"title": "Learning to Plan with Agents", "content": "LLM agents use planning and memory."},
            {"title": "Agent Fine-tuning", "content": "Agents learn from failed trajectories."},
        ],
    }
    result = evaluate_node(state)
    assert rule_based_score(state) < 0.7
    assert result["retrieval_outcome"] == "replan_required"
    assert result["retrieval_evaluation"]["failure_type"] == "topic_coverage_missing"
    assert set(result["retrieval_evaluation"]["topic_coverage"]["missing_groups"]) == {"harness", "workflow"}


def test_harness_and_workflow_evidence_can_pass_hard_coverage():
    state = {
        **_state(),
        "documents": [
            {"title": "Agent Evaluation Harness", "content": "A tool sandbox and runtime infrastructure for LLM agents."},
            {"title": "Workflow Orchestration for Agents", "content": "A state machine and task graph execute agent workflows."},
            {"title": "Agent Scaffolding", "content": "Scaffolding supports tool-using language agents."},
        ],
    }
    result = evaluate_node(state)
    assert result["retrieval_score"] >= 0.7
    assert result["retrieval_evaluation"]["topic_coverage"]["passed"] is True


def test_missing_harness_groups_receive_targeted_single_replan():
    state = {
        **_state(), "documents": [{"title": "Agent Planning", "content": "LLM agent planning"}],
        "retrieval_score": 0.58,
        "retrieval_evaluation": {
            "failure_type": "topic_coverage_missing",
            "topic_coverage": {"missing_groups": ["harness", "workflow"]},
        },
    }
    result = build_retrieval_replan(state)
    assert result["retrieval_replan"]["action"] == "target_missing_topic_groups"
    assert all(term in result["retry_query"] for term in ("harness", "scaffolding", "runtime", "evaluation", "infrastructure"))
    assert all(term in result["retry_query"] for term in ("workflow", "orchestration", "state machine"))


def test_harness_online_scope_uses_arxiv_and_openalex(monkeypatch):
    from retrieval import strategy
    monkeypatch.setattr(strategy.settings, "RETRIEVAL_MODE", "arxiv")
    result = select_retrieval_strategy({**_state(), "retrieval_scope": "online"})
    assert result["sources"] == ["arxiv", "openalex"]
