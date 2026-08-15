import pytest
from pydantic import ValidationError

from multi_agent.contracts import MultiAgentTrace
from multi_agent.orchestrator import build_multi_agent_trace


def _l3_state():
    return {
        "task_level": "L3",
        "research_plan_validation": {"valid": True, "errors": []},
        "research_plan": {"tasks": [{"task_id": "T1"}, {"task_id": "T2"}]},
        "research_schedule": {"waves": [{"wave": 1}], "max_parallel_tasks": 2},
        "evidence_store": {"evidence_count": 3},
        "research_coverage": {"status": "passed", "coverage_pct": 100.0},
        "answer_verification": {"passed": True, "failure_types": []},
        "citation_validation": {"enabled": True, "passed": True},
        "citation_repair": {"status": "not_needed"},
        "answer_reflection_count": 0,
    }


def test_bounded_multi_agent_trace_composes_existing_l3_roles_without_extra_llm():
    trace = build_multi_agent_trace(_l3_state())

    assert trace["enabled"] is True
    assert trace["status"] == "completed"
    assert [item["role"] for item in trace["handoffs"]] == ["planner", "executor", "reviewer"]
    assert trace["additional_llm_calls"] == 0
    assert trace["max_review_loops"] == 1


def test_multi_agent_trace_preserves_blocked_evidence_and_review_failures():
    state = _l3_state()
    state["research_coverage"] = {"status": "blocked", "coverage_pct": 0.0}
    state["answer_verification"] = {"passed": False, "failure_types": ["missing_evidence_reference"]}

    trace = build_multi_agent_trace(state)

    assert trace["status"] == "blocked"
    assert trace["handoffs"][1]["failure_reason"] == "evidence_coverage_incomplete"
    assert "missing_evidence_reference" in trace["handoffs"][2]["failure_reason"]


def test_multi_agent_stays_off_for_fast_path_and_contract_caps_review_loop():
    trace = build_multi_agent_trace({"task_level": "L1"})
    assert trace["status"] == "not_applicable"
    assert trace["handoffs"] == []

    with pytest.raises(ValidationError):
        MultiAgentTrace(enabled=True, status="completed", max_review_loops=2)
