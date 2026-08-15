from agent.state import AgentState
from validators.pdf_grounding_validator import validate_pdf_grounding


def pdf_grounding_validate_node(state: AgentState) -> AgentState:
    result = validate_pdf_grounding(state)
    return {
        "pdf_grounding_validation": result,
        "paper_metadata": {
            **state.get("paper_metadata", {}),
            "pdf_grounding_validation": result,
        },
    }
