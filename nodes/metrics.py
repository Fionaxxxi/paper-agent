from agent.state import AgentState


def metrics_node(state: AgentState) -> AgentState:
    documents = state.get("documents", [])
    tools_used = state.get("tools_used", [])
    node_timings = state.get("node_timings", {})

    total_time = round(sum(node_timings.values()), 2)

    metrics = {
        "retrieval_count": len(documents),
        "retrieval_score": state.get("retrieval_score", 0.0),
        "retry_count": state.get("retry_count", 0),
        "tool_count": len(tools_used),
        "tools_used": tools_used,
        "task_type": state.get("task_type", "unknown"),
        "rewritten_query": state.get("rewritten_query", ""),
        "total_time": total_time,
        "node_timings": node_timings,
    }

    print("\n=== Metrics ===")
    print(f"retrieval_count: {metrics['retrieval_count']}")
    print(f"retrieval_score: {metrics['retrieval_score']}")
    print(f"retry_count: {metrics['retry_count']}")
    print(f"tool_count: {metrics['tool_count']}")
    print(f"tools_used: {metrics['tools_used']}")
    print(f"task_type: {metrics['task_type']}")
    print(f"rewritten_query: {metrics['rewritten_query']}")
    print(f"skill_used: {state.get('paper_metadata', {}).get('skill_used', '')}")
    print(f"citation_format: {state.get('paper_metadata', {}).get('citation_format', '')}")
    paper_metadata = state.get("paper_metadata", {})
    print(f"reason_source: {paper_metadata.get('reason_source', '')}")
    print(f"reason_confidence: {paper_metadata.get('reason_confidence', '')}")
    print(f"rule_task_type: {paper_metadata.get('rule_task_type', '')}")

    print("\n=== Node Timings ===")
    for node_name, elapsed in node_timings.items():
        print(f"{node_name}: {elapsed}s")

    print(f"total: {total_time}s")

    return {
        "paper_metadata": {
            **state.get("paper_metadata", {}),
            "metrics": metrics,
        }
    }