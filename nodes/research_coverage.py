from agent.state import AgentState
from research.coverage import evaluate_evidence_coverage


def research_coverage_node(state: AgentState) -> AgentState:
    coverage = evaluate_evidence_coverage(state.get("evidence_store", {}))
    return {
        "research_coverage": coverage,
        "paper_metadata": {
            **state.get("paper_metadata", {}),
            "research_coverage_status": coverage["status"],
            "research_coverage_pct": coverage["coverage_pct"],
        },
    }
