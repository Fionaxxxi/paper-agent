from agent.state import AgentState
from validators.claim_evidence_validator import validate_claim_evidence


def claim_evidence_validate_node(state: AgentState) -> AgentState:
    result = validate_claim_evidence(state)
    return {
        "claim_evidence_validation": result.model_dump(mode="python"),
        "paper_metadata": {
            **state.get("paper_metadata", {}),
            "claim_evidence_validation_status": result.status,
            "claim_evidence_support_rate_pct": result.support_rate_pct,
        },
    }
