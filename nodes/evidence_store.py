from agent.state import AgentState
from research.evidence_store import build_evidence_store


def evidence_store_node(state: AgentState) -> AgentState:
    schedule = state.get("research_schedule", {})
    if not schedule.get("enabled"):
        return {"evidence_store": {"enabled": False, "evidence": [],
                                   "status": "not_applicable"}}
    documents = [*state.get("documents", []), *state.get("repository_evidence", [])]
    store = build_evidence_store(schedule, documents)
    return {
        "evidence_store": store,
        "paper_metadata": {
            **state.get("paper_metadata", {}),
            "evidence_store_status": store["status"],
            "evidence_count": store["evidence_count"],
            "claim_evidence_input_count": len(store["claim_evidence_inputs"]),
        },
    }
