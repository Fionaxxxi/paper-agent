from agent.state import AgentState


def route_after_guardrail(state: AgentState) -> str:
    if not state.get("is_valid", True):
        return "end"

    return "retrieve"


def route_after_evaluate(state: AgentState) -> str:
    score = state.get("retrieval_score", 0.0)
    retry_count = state.get("retry_count", 0)

    if score < 0.7 and retry_count < 1:
        return "retry"

    return "generate"