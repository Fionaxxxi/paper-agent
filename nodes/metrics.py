from agent.state import AgentState


def metrics_node(state: AgentState) -> AgentState:
    documents = state.get("documents", [])
    tools_used = state.get("tools_used", [])

    metrics = {
        "retrieval_count": len(documents),
        "retrieval_score": state.get("retrieval_score", 0.0),
        "retry_count": state.get("retry_count", 0),
        "tool_count": len(tools_used),
        "tools_used": tools_used,
    }

    print("\n=== Metrics ===")
    for key, value in metrics.items():
        print(f"{key}: {value}")

    return {
        "paper_metadata": {
            **state.get("paper_metadata", {}),
            "metrics": metrics,
        }
    }