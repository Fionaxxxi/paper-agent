from agent.state import AgentState
from retrieval.strategy import select_retrieval_strategy


def retrieval_route_node(state: AgentState) -> AgentState:
    strategy = select_retrieval_strategy(state)
    return {
        "retrieval_strategy": strategy,
        "paper_metadata": {
            **state.get("paper_metadata", {}),
            "retrieval_strategy": strategy,
        },
    }
