"""零 LLM 的指代消解与主动澄清门控。"""

from __future__ import annotations

import re
from typing import Any

from agent.state import AgentState


REFERENCE_PATTERNS = (
    "这个方法", "该方法", "上述方法", "这种方法", "这个模型", "该模型",
    "这篇论文", "该论文", "那篇论文", "刚才那个", "刚才的", "它",
)


def find_references(query: str) -> list[str]:
    return [pattern for pattern in REFERENCE_PATTERNS if pattern in query]


def _unique(values: list[str], limit: int = 5) -> list[str]:
    result = []
    for value in values:
        normalized = str(value or "").strip()
        if normalized and normalized not in result:
            result.append(normalized)
        if len(result) >= limit:
            break
    return result


def clarification_candidates(state: AgentState, references: list[str]) -> list[str]:
    metadata = state.get("paper_metadata", {})
    papers = _unique(metadata.get("memory_active_papers", []))
    topics = _unique(metadata.get("memory_active_topics", []))
    paper_reference = any("论文" in reference for reference in references)
    return _unique(papers if paper_reference and papers else [*papers, *topics])


def resolve_pending_answer(answer: str, candidates: list[str]) -> str:
    normalized = answer.strip().casefold().strip(" ，。,.!?！？")
    exact = [item for item in candidates if item.casefold() == normalized]
    if len(exact) == 1:
        return exact[0]
    contained = [item for item in candidates if item.casefold() in normalized]
    if len(contained) == 1:
        return contained[0]
    ordinal = re.fullmatch(r"第?([一二三123])个?", normalized)
    if ordinal:
        index = {"一": 0, "1": 0, "二": 1, "2": 1, "三": 2, "3": 2}[ordinal.group(1)]
        if index < len(candidates):
            return candidates[index]
    return ""


def replace_references(query: str, references: list[str], referent: str) -> str:
    resolved = query
    for reference in references:
        resolved = resolved.replace(reference, referent)
    return resolved


def _clarification_response(
    state: AgentState, query: str, candidates: list[str], references: list[str]
) -> AgentState:
    if candidates:
        choices = "、".join(candidates[:3])
        question = f"我暂时无法确定你指的是哪一个。你指的是：{choices}？"
    else:
        question = "我暂时无法确定你指的对象。请补充具体的论文、方法或模型名称。"
    pending = {
        "query": query,
        "candidates": candidates,
        "references": references,
        "question": question,
    }
    return {
        "clarification_required": True,
        "clarification_question": question,
        "clarification_candidates": candidates,
        "pending_clarification": pending,
        "task_type": "clarification",
        "answer": question,
        "documents": [],
        "llm_call_count": state.get("llm_call_count", 0),
        "llm_failed_call_count": state.get("llm_failed_call_count", 0),
        "token_usage": state.get("token_usage", 0),
        "input_token_usage": state.get("input_token_usage", 0),
        "output_token_usage": state.get("output_token_usage", 0),
        "llm_usage": list(state.get("llm_usage", [])),
        "paper_metadata": {
            **state.get("paper_metadata", {}),
            "clarification_required": True,
            "clarification_reason": "unresolved_reference",
            "short_circuited": True,
        },
    }


def clarification_node(state: AgentState) -> AgentState:
    query = state.get("query", "").strip()
    pending: dict[str, Any] = state.get("pending_clarification", {}) or {}
    if pending:
        candidates = _unique(pending.get("candidates", []))
        referent = resolve_pending_answer(query, candidates)
        if referent:
            original = pending.get("query", "")
            references = pending.get("references", find_references(original))
            resolved = replace_references(original, references, referent)
            return {
                "query": resolved,
                "original_query": query,
                "resolved_query": resolved,
                "resolved_referent": referent,
                "clarification_required": False,
                "clarification_question": "",
                "clarification_candidates": [],
                "pending_clarification": {},
                "paper_metadata": {
                    **state.get("paper_metadata", {}),
                    "clarification_required": False,
                    "clarification_resolved": True,
                    "resolved_referent": referent,
                    "resolved_query": resolved,
                },
            }
        # 用户仍只给出无法识别的短回答时继续等待；完整新问题则放弃旧等待。
        if len(query) <= 20 and not find_references(query):
            return _clarification_response(
                state, pending.get("query", ""), candidates,
                pending.get("references", []),
            )

    references = find_references(query)
    if not references:
        return {
            "clarification_required": False,
            "pending_clarification": {},
        }
    candidates = clarification_candidates(state, references)
    if len(candidates) == 1:
        resolved = replace_references(query, references, candidates[0])
        return {
            "query": resolved,
            "original_query": query,
            "resolved_query": resolved,
            "resolved_referent": candidates[0],
            "clarification_required": False,
            "pending_clarification": {},
            "paper_metadata": {
                **state.get("paper_metadata", {}),
                "clarification_resolved": True,
                "resolved_referent": candidates[0],
                "resolved_query": resolved,
            },
        }
    return _clarification_response(state, query, candidates, references)
