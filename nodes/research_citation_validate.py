from agent.state import AgentState
from validators.research_citation_validator import validate_research_citations


def research_citation_validate_node(state: AgentState) -> AgentState:
    result = validate_research_citations(state)
    return {
        "citation_validation": result.model_dump(mode="python"),
        "paper_metadata": {
            **state.get("paper_metadata", {}),
            "citation_validation_status": result.status,
        },
    }
