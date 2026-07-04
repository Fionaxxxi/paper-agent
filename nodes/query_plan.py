from typing import Any, Dict, List

from agent.state import AgentState


def deduplicate_queries(queries: List[str]) -> List[str]:
    """
    Deduplicate query strings while preserving order.
    """

    seen = set()
    deduplicated = []

    for query in queries:
        normalized_query = query.strip()

        if not normalized_query:
            continue

        key = normalized_query.lower()

        if key in seen:
            continue

        seen.add(key)
        deduplicated.append(normalized_query)

    return deduplicated


def build_rule_based_sub_queries(state: Dict[str, Any]) -> List[str]:
    """
    Build sub queries using lightweight rules.

    This is the first version of Query Planning. It avoids extra LLM calls
    and keeps the Agentic RAG stage stable.
    """

    query = state.get("query", "")
    rewritten_query = state.get("rewritten_query", "") or query
    task_type = state.get("task_type", "qa")

    sub_queries = [rewritten_query]

    if task_type == "compare":
        sub_queries.extend(
            [
                f"{rewritten_query} methods comparison",
                f"{rewritten_query} evaluation metrics",
                f"{rewritten_query} limitations",
            ]
        )

    elif task_type == "summarize":
        sub_queries.extend(
            [
                f"{rewritten_query} survey overview",
                f"{rewritten_query} methods",
                f"{rewritten_query} contributions",
            ]
        )

    elif task_type == "recommend":
        sub_queries.extend(
            [
                f"{rewritten_query} open problems",
                f"{rewritten_query} future research directions",
                f"{rewritten_query} limitations challenges",
            ]
        )

    elif task_type == "citation":
        sub_queries.extend(
            [
                f"{rewritten_query} arxiv",
                f"{rewritten_query} recent papers",
            ]
        )

    else:
        sub_queries.extend(
            [
                f"{rewritten_query} recent research",
                f"{rewritten_query} methods",
            ]
        )

    return deduplicate_queries(sub_queries)


def query_plan_node(state: AgentState) -> AgentState:
    """
    Build retrieval sub_queries for Agentic RAG.

    PDF reading tasks do not need query planning because they analyze
    uploaded PDF text directly.
    """

    task_type = state.get("task_type", "qa")

    if task_type == "pdf_reading":
        return {
            "sub_queries": [],
            "query_plan_enabled": False,
            "query_plan_reason": "pdf_reading task does not require retrieval planning",
        }

    sub_queries = build_rule_based_sub_queries(state)

    return {
        "sub_queries": sub_queries,
        "query_plan_enabled": True,
        "query_plan_reason": "rule_based_query_plan",
        "paper_metadata": {
            **state.get("paper_metadata", {}),
            "sub_queries": sub_queries,
            "sub_query_count": len(sub_queries),
            "query_plan_enabled": True,
        },
    }