from agent.state import AgentState
from core.config import settings


def build_llm_usage_by_node(records: list[dict]) -> dict:
    usage_by_node = {}

    for record in records:
        node_name = record.get("node_name", "unknown")
        node_usage = usage_by_node.setdefault(
            node_name,
            {
                "call_count": 0,
                "failed_call_count": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "latency_seconds": 0.0,
            },
        )
        node_usage["call_count"] += 1
        if not record.get("success", False):
            node_usage["failed_call_count"] += 1
        node_usage["input_tokens"] += record.get("input_tokens", 0)
        node_usage["output_tokens"] += record.get("output_tokens", 0)
        node_usage["total_tokens"] += record.get("total_tokens", 0)
        node_usage["latency_seconds"] = round(
            node_usage["latency_seconds"]
            + record.get("latency_seconds", 0.0),
            4,
        )

    return usage_by_node


def metrics_node(state: AgentState) -> AgentState:
    documents = state.get("documents", [])
    tools_used = state.get("tools_used", [])
    node_timings = state.get("node_timings", {})
    paper_metadata = state.get("paper_metadata", {})
    task_type = state.get("task_type", "unknown")
    llm_usage = state.get("llm_usage", [])
    tool_executions = paper_metadata.get("tool_executions", [])

    total_time = round(sum(node_timings.values()), 2)
    input_token_usage = state.get("input_token_usage", 0)
    output_token_usage = state.get("output_token_usage", 0)
    estimated_cost = round(
        (
            input_token_usage
            * settings.MODEL_INPUT_COST_PER_1M_TOKENS
            + output_token_usage
            * settings.MODEL_OUTPUT_COST_PER_1M_TOKENS
        )
        / 1_000_000,
        8,
    )

    sub_queries = paper_metadata.get(
        "sub_queries",
        state.get("sub_queries", []),
    )

    metrics = {
        # Retrieval
        "retrieval_count": len(documents),
        "retrieval_score": state.get("retrieval_score", 0.0),
        "retrieval_source": paper_metadata.get("retrieval_source", ""),
        "cache_hit": paper_metadata.get("cache_hit", False),
        "retry_count": state.get("retry_count", 0),

        # Agentic RAG / Query Planning
        "query_plan_enabled": paper_metadata.get(
            "query_plan_enabled",
            state.get("query_plan_enabled", False),
        ),
        "agentic_rag_enabled": paper_metadata.get(
            "agentic_rag_enabled",
            False,
        ),
        "sub_query_count": paper_metadata.get(
            "sub_query_count",
            len(sub_queries),
        ),
        "planned_query_count": paper_metadata.get(
            "planned_query_count",
            len(sub_queries),
        ),
        "query_complexity": paper_metadata.get(
            "query_complexity",
            state.get("query_complexity", ""),
        ),
        "complexity_reason": paper_metadata.get(
            "complexity_reason",
            state.get("complexity_reason", ""),
        ),
        "sub_queries": sub_queries,
        "raw_document_count": paper_metadata.get(
            "raw_document_count",
            len(documents),
        ),
        "merged_document_count": paper_metadata.get(
            "merged_document_count",
            len(documents),
        ),
        "deduplicated_count": paper_metadata.get(
            "deduplicated_count",
            0,
        ),
        "retrieval_sources": paper_metadata.get(
            "retrieval_sources",
            [],
        ),
        "cache_hit_count": paper_metadata.get(
            "cache_hit_count",
            0,
        ),

        # Task
        "task_type": task_type,
        "is_pdf_task": task_type == "pdf_reading",

        # Tool
        "tool_count": len(tools_used),
        "tools_used": tools_used,
        "tool_execution_count": len(tool_executions),
        "tool_success_count": sum(
            execution.get("tool_success", False)
            for execution in tool_executions
        ),
        "tool_failure_count": sum(
            not execution.get("tool_success", False)
            for execution in tool_executions
        ),
        "tool_latency_seconds": round(
            sum(
                execution.get("tool_latency_seconds", 0.0)
                for execution in tool_executions
            ),
            4,
        ),
        "tool_executions": tool_executions,

        # LLM usage
        "llm_call_count": state.get("llm_call_count", 0),
        "llm_failed_call_count": state.get("llm_failed_call_count", 0),
        "input_token_usage": input_token_usage,
        "output_token_usage": output_token_usage,
        "token_usage": state.get("token_usage", 0),
        "llm_latency_seconds": round(
            sum(
                record.get("latency_seconds", 0.0)
                for record in llm_usage
            ),
            4,
        ),
        "llm_usage_unavailable_count": sum(
            1
            for record in llm_usage
            if not record.get("token_usage_available", False)
        ),
        "llm_usage_by_node": build_llm_usage_by_node(llm_usage),
        "estimated_cost": estimated_cost,
        "cost_estimation_enabled": bool(
            settings.MODEL_INPUT_COST_PER_1M_TOKENS
            or settings.MODEL_OUTPUT_COST_PER_1M_TOKENS
        ),
        "model_name": settings.MODEL_NAME,

        # Reason / Skill
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

    print("\n[Agentic RAG]")
    print(f"query_plan_enabled: {metrics['query_plan_enabled']}")
    print(f"agentic_rag_enabled: {metrics['agentic_rag_enabled']}")
    print(f"sub_query_count: {metrics['sub_query_count']}")
    print(f"planned_query_count: {metrics['planned_query_count']}")
    print(f"query_complexity: {metrics['query_complexity']}")
    print(f"complexity_reason: {metrics['complexity_reason']}")
    print(f"sub_queries: {metrics['sub_queries']}")
    print(f"raw_document_count: {metrics['raw_document_count']}")
    print(f"merged_document_count: {metrics['merged_document_count']}")
    print(f"deduplicated_count: {metrics['deduplicated_count']}")
    print(f"retrieval_sources: {metrics['retrieval_sources']}")
    print(f"cache_hit_count: {metrics['cache_hit_count']}")

    print("\n[Task]")
    print(f"task_type: {metrics['task_type']}")
    print(f"is_pdf_task: {metrics['is_pdf_task']}")

    print("\n[Tool]")
    print(f"tool_count: {metrics['tool_count']}")
    print(f"tools_used: {metrics['tools_used']}")
    print(f"tool_execution_count: {metrics['tool_execution_count']}")
    print(f"tool_success_count: {metrics['tool_success_count']}")
    print(f"tool_failure_count: {metrics['tool_failure_count']}")
    print(f"tool_latency_seconds: {metrics['tool_latency_seconds']}")

    print("\n[LLM Usage]")
    print(f"llm_call_count: {metrics['llm_call_count']}")
    print(f"llm_failed_call_count: {metrics['llm_failed_call_count']}")
    print(f"input_token_usage: {metrics['input_token_usage']}")
    print(f"output_token_usage: {metrics['output_token_usage']}")
    print(f"token_usage: {metrics['token_usage']}")
    print(f"llm_latency_seconds: {metrics['llm_latency_seconds']}")
    print(f"llm_usage_by_node: {metrics['llm_usage_by_node']}")
    print(f"estimated_cost: {metrics['estimated_cost']}")

    print("\n[Reason / Skill]")
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
