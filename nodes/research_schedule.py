from agent.state import AgentState
from research.scheduler import build_schedule


def research_schedule_node(state: AgentState) -> AgentState:
    if (
        state.get("task_level") != "L3"
        or not state.get("research_plan_validation", {}).get("valid")
    ):
        return {"research_schedule": {"enabled": False, "waves": [],
                                      "status": "not_applicable"}}
    schedule = build_schedule(state.get("research_plan", {}))
    return {
        "research_schedule": schedule,
        "paper_metadata": {
            **state.get("paper_metadata", {}),
            "research_schedule_status": schedule["status"],
            "research_schedule_wave_count": len(schedule["waves"]),
            "research_schedule_max_parallel": schedule["max_parallel_tasks"],
        },
    }
