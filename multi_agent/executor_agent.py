from multi_agent.contracts import AgentHandoff


def build_executor_handoff(state: dict) -> AgentHandoff:
    coverage = state.get("research_coverage", {})
    store = state.get("evidence_store", {})
    coverage_status = coverage.get("status", "blocked")
    status = "completed" if coverage_status == "passed" else "partial" if coverage_status == "partial" else "blocked"
    return AgentHandoff(
        role="executor",
        status=status,
        input_refs=["research_schedule", "tool_executions"],
        output_summary={
            "evidence_count": store.get("evidence_count", 0),
            "coverage_status": coverage_status,
            "coverage_pct": coverage.get("coverage_pct", 0.0),
        },
        failure_reason="" if status == "completed" else "evidence_coverage_incomplete",
    )
