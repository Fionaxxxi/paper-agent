from multi_agent.contracts import MultiAgentTrace
from multi_agent.executor_agent import build_executor_handoff
from multi_agent.planner_agent import build_planner_handoff
from multi_agent.reviewer_agent import build_reviewer_handoff


def build_multi_agent_trace(state: dict) -> dict:
    if state.get("task_level") != "L3":
        return MultiAgentTrace(enabled=False, status="not_applicable").model_dump(mode="python")

    handoffs = [
        build_planner_handoff(state),
        build_executor_handoff(state),
        build_reviewer_handoff(state),
    ]
    statuses = {handoff.status for handoff in handoffs}
    status = "blocked" if "blocked" in statuses else "partial" if "partial" in statuses else "completed"
    trace = MultiAgentTrace(
        enabled=True,
        status=status,
        max_review_loops=1,
        actual_review_loops=min(state.get("answer_reflection_count", 0), 1),
        additional_llm_calls=0,
        handoffs=handoffs,
    )
    return trace.model_dump(mode="python")
