from agent.state import AgentState
from multi_agent.orchestrator import build_multi_agent_trace


def multi_agent_finalize_node(state: AgentState) -> AgentState:
    trace = build_multi_agent_trace(state)
    return {
        "multi_agent_trace": trace,
        "paper_metadata": {**state.get("paper_metadata", {}), "multi_agent_trace": trace},
    }
