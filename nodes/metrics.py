import time

from agent.state import AgentState


def metrics_node(state: AgentState) -> AgentState:
    documents = state.get("documents", [])
    tools_used = state.get("tools_used", [])
    node_timings = state.get("node_timings", {})
    paper_metadata = state.get("paper_metadata", {})
    task_type = state.get("task_type", "unknown")

    total_time = round(sum(node_timings.values()), 2)

    metrics = {
        # Retrieval
        "retrieval_count": len(documents),
        "retrieval_score": state.get("retrieval_score", 0.0),
        "retrieval_source": paper_metadata.get("retrieval_source", ""),
        "cache_hit": paper_metadata.get("cache_hit", False),
        "retry_count": state.get("retry_count", 0),

        #Tasktype
        "task_type": task_type,
        "is_pdf_task": task_type == "pdf_reading",

        # Tool
        "tool_count": len(tools_used),
        "tools_used": tools_used,

        # Reason / Skill
        "task_type": state.get("task_type", "unknown"),
        "rewritten_query": state.get("rewritten_query", ""),
        "reason_source": paper_metadata.get("reason_source", ""),
        "reason_confidence": paper_metadata.get("reason_confidence", ""),
        "rule_task_type": paper_metadata.get("rule_task_type", ""),
        "skill_used": paper_metadata.get("skill_used", ""),
        "citation_format": paper_metadata.get("citation_format", ""),

        # Memory
        "conversation_id": state.get("conversation_id", ""),
        "history_count": len(state.get("history", [])),

        # PDF
        "pdf_path": state.get("pdf_path", ""),
        "pdf_page_count": state.get("pdf_page_count", 0),
        "pdf_error": state.get("pdf_error", ""),

        # Timing
        "total_time": total_time,
        "node_timings": node_timings,
    }

    print_metrics(metrics)

    return {
        "paper_metadata": {
            **paper_metadata,
            "metrics": metrics,
        }
    }


def print_metrics(metrics: dict) -> None:
    print("\n=== Metrics ===")

    print("\n[Retrieval]")
    print(f"retrieval_count: {metrics['retrieval_count']}")
    print(f"retrieval_score: {metrics['retrieval_score']}")
    print(f"retrieval_source: {metrics['retrieval_source']}")
    print(f"cache_hit: {metrics['cache_hit']}")
    print(f"retry_count: {metrics['retry_count']}")

    print("\n[Task]")
    print(f"is_pdf_task: {metrics['is_pdf_task']}")

    print("\n[Tool]")
    print(f"tool_count: {metrics['tool_count']}")
    print(f"tools_used: {metrics['tools_used']}")

    print("\n[Reason / Skill]")
    print(f"task_type: {metrics['task_type']}")
    print(f"rewritten_query: {metrics['rewritten_query']}")
    print(f"reason_source: {metrics['reason_source']}")
    print(f"reason_confidence: {metrics['reason_confidence']}")
    print(f"rule_task_type: {metrics['rule_task_type']}")
    print(f"skill_used: {metrics['skill_used']}")
    print(f"citation_format: {metrics['citation_format']}")

    print("\n[Memory]")
    print(f"conversation_id: {metrics['conversation_id']}")
    print(f"history_count: {metrics['history_count']}")

    print("\n[PDF]")
    print(f"pdf_path: {metrics['pdf_path']}")
    print(f"pdf_page_count: {metrics['pdf_page_count']}")
    print(f"pdf_error: {metrics['pdf_error']}")

    print("\n[Timing]")
    print(f"total_time: {metrics['total_time']}")
    print(f"node_timings: {metrics['node_timings']}")