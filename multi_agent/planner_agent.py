from multi_agent.contracts import AgentHandoff


def build_planner_handoff(state: dict) -> AgentHandoff:
    validation = state.get("research_plan_validation", {})
    plan = state.get("research_plan", {})
    schedule = state.get("research_schedule", {})
    valid = bool(validation.get("valid"))
    return AgentHandoff(
        role="planner",
        status="completed" if valid else "blocked",
        input_refs=["research_analysis", "research_brief"],
        output_summary={
            "task_count": len(plan.get("tasks", [])),
            "wave_count": len(schedule.get("waves", [])),
            "max_parallel_tasks": schedule.get("max_parallel_tasks", 0),
        },
        failure_reason="" if valid else "; ".join(validation.get("errors", [])) or "invalid_research_plan",
    )
