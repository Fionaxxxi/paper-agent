from agent.state import AgentState
from research.citation_repair import repair_uncited_synthesis


def research_citation_repair_node(state: AgentState) -> AgentState:
    result = repair_uncited_synthesis(state)
    update = {
        "citation_repair": {key: value for key, value in result.items() if key != "answer"},
        "paper_metadata": {
            **state.get("paper_metadata", {}),
            "citation_repair_status": result["status"],
        },
    }
    if result["status"] in {"repaired", "partially_repaired"}:
        update["answer"] = result["answer"]
        update["citation_validation"] = result["validation_after"]
    return update
