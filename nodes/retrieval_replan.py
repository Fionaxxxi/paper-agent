"""Deterministic, bounded retrieval replanning from observable failure types."""

from __future__ import annotations

import re
from typing import Any

from agent.state import AgentState

TRANSIENT_TOOL_ERRORS = {"TIMEOUT", "NETWORK_ERROR", "RATE_LIMITED", "EXECUTION_ERROR"}


def _tool_failure_codes(state: AgentState) -> list[str]:
    executions = state.get("paper_metadata", {}).get("tool_executions", [])
    return [
        str(row.get("tool_error_code", ""))
        for row in executions
        if not row.get("tool_success", False) and row.get("tool_error_code")
    ]


def _base_query(state: AgentState) -> str:
    metadata = state.get("paper_metadata", {})
    return str(
        metadata.get("search_query")
        or state.get("rewritten_query")
        or state.get("query", "")
    ).strip()


def build_retrieval_replan(state: AgentState) -> dict[str, Any]:
    """Return one auditable repair action; the graph enforces the retry budget."""
    query = _base_query(state)
    codes = _tool_failure_codes(state)
    documents = state.get("documents", [])
    score = float(state.get("retrieval_score", 0.0))

    if any(code in TRANSIENT_TOOL_ERRORS for code in codes):
        failure_type = "transient_tool_failure"
        action = "retry_same_query"
        replanned_query = query
        reason = f"检测到可恢复工具错误：{', '.join(codes)}"
    elif not documents:
        failure_type = "empty_results"
        action = "broaden_query"
        normalized = re.sub(r'["“”()（）]', " ", query)
        normalized = " ".join(normalized.split())
        replanned_query = f"{normalized} research survey".strip()
        reason = "检索结果为空，放宽字面约束并增加综述检索词"
    else:
        failure_type = "low_relevance"
        action = "expand_context"
        replanned_query = f"{query} survey review".strip()
        reason = f"已有结果但相关性评分 {score:.2f} 低于门槛"

    return {
        "retry_count": state.get("retry_count", 0) + 1,
        "retrieval_replan": {
            "failure_type": failure_type,
            "action": action,
            "original_query": query,
            "replanned_query": replanned_query,
            "reason": reason,
            "tool_failure_codes": codes,
        },
        "retry_query": replanned_query,
    }
