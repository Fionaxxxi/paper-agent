"""零 LLM 的指代消解与主动澄清门控。"""

from __future__ import annotations

import re
import json
from typing import Any

from langchain_openai import ChatOpenAI

from agent.state import AgentState
from core.config import settings
from core.llm_usage import TrackedLLMError, build_llm_usage_update, invoke_llm_with_usage
from prompts.contracts import get_prompt_version


REFERENCE_PATTERNS = (
    "这个方法", "该方法", "上述方法", "这种方法", "这个模型", "该模型",
    "这篇论文", "该论文", "那篇论文", "刚才那个", "刚才的", "它",
)
ORDINAL_REFERENCE_RE = re.compile(r"第(?P<number>\d+|[一二三四五六七八九十]+)(?:篇|个)(?:论文|方法|模型)?")
DESCRIPTIVE_REFERENCE_RE = re.compile(r"那个.{2,40}?(?:方法|模型|论文)")


def find_references(query: str) -> list[str]:
    references = [pattern for pattern in REFERENCE_PATTERNS if pattern in query]
    references.extend(match.group(0) for match in ORDINAL_REFERENCE_RE.finditer(query))
    references.extend(match.group(0) for match in DESCRIPTIVE_REFERENCE_RE.finditer(query))
    return _unique(references)


def _ordinal_value(text: str) -> int | None:
    match = ORDINAL_REFERENCE_RE.search(text)
    if not match:
        return None
    raw = match.group("number")
    if raw.isdigit():
        return int(raw)
    digits = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
    if raw == "十":
        return 10
    if "十" in raw:
        left, _, right = raw.partition("十")
        return digits.get(left, 1) * 10 + digits.get(right, 0)
    return digits.get(raw)


def validate_candidate(candidate: str, confidence: float, candidates: list[str]) -> str:
    exact = [item for item in candidates if item.casefold() == candidate.strip().casefold()]
    if len(exact) == 1 and confidence >= settings.CLARIFICATION_SEMANTIC_CONFIDENCE_THRESHOLD:
        return exact[0]
    return ""


def resolve_semantic_candidate(query: str, candidates: list[str]):
    """只在描述性指代且存在多个候选时调用现有主模型一次。"""
    llm = ChatOpenAI(
        model=settings.MODEL_NAME, api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL, temperature=0,
        timeout=settings.LLM_TIMEOUT, max_retries=1,
    )
    prompt = (
        "根据用户描述，从候选列表中选择唯一指代对象。只输出严格JSON："
        '{"candidate":"候选原文或空字符串","confidence":0到1}。'
        "不得创造候选，不确定时candidate为空。\n"
        f"用户问题：{query}\n候选列表：{json.dumps(candidates, ensure_ascii=False)}"
    )
    response, usage = invoke_llm_with_usage(
        llm, prompt, "clarification", settings.MODEL_NAME,
        prompt_version=get_prompt_version("clarification_resolve"),
    )
    text = response.content.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    payload = json.loads(fenced.group(1) if fenced else text)
    candidate = validate_candidate(
        str(payload.get("candidate", "")), float(payload.get("confidence", 0.0)), candidates
    )
    return candidate, usage


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


def _resolved_response(
    state: AgentState, query: str, references: list[str], referent: str,
    resolution_source: str, usage_update: dict[str, Any] | None = None,
) -> AgentState:
    usage_update = usage_update or {}
    resolved = replace_references(query, references, referent)
    return {
        **usage_update,
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
            **usage_update.get("paper_metadata", {}),
            "clarification_required": False,
            "clarification_resolved": True,
            "clarification_resolution_source": resolution_source,
            "resolved_referent": referent,
            "resolved_query": resolved,
        },
    }


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
    metadata = state.get("paper_metadata", {})
    selected_document_title = str(metadata.get("selected_document_title", "")).strip()
    selected_document_id = str(metadata.get("selected_document_id", "")).strip()
    # “基于此论文提问”是用户本轮的显式选择，优先级高于会话历史候选。
    # 序数指代仍按候选顺序解析，避免把“第二篇论文”错误绑定到当前文档。
    if selected_document_id and selected_document_title and _ordinal_value(query) is None:
        return _resolved_response(
            state,
            query,
            references,
            selected_document_title,
            "selected_document",
        )
    candidates = clarification_candidates(state, references)
    ordinal = _ordinal_value(query)
    if ordinal is not None:
        if 1 <= ordinal <= len(candidates):
            return _resolved_response(
                state, query, references, candidates[ordinal - 1], "ordinal_rule"
            )
        response = _clarification_response(state, query, candidates, references)
        response["paper_metadata"]["clarification_reason"] = "ordinal_out_of_range"
        response["paper_metadata"]["requested_ordinal"] = ordinal
        return response
    if len(candidates) == 1:
        return _resolved_response(state, query, references, candidates[0], "unique_rule")
    descriptive = any(DESCRIPTIVE_REFERENCE_RE.fullmatch(reference) for reference in references)
    if descriptive and len(candidates) > 1 and settings.CLARIFICATION_SEMANTIC_WITH_LLM:
        usage_update: dict[str, Any] = {}
        try:
            referent, usage = resolve_semantic_candidate(query, candidates)
            usage_update = build_llm_usage_update(state, usage)
            if referent:
                return _resolved_response(
                    state, query, references, referent, "semantic_llm", usage_update
                )
        except TrackedLLMError as error:
            usage_update = build_llm_usage_update(state, error.usage_record)
        except Exception:
            usage_update = {}
        response = _clarification_response(state, query, candidates, references)
        response.update({key: value for key, value in usage_update.items() if key != "paper_metadata"})
        response["paper_metadata"]["clarification_semantic_attempted"] = True
        return response
    return _clarification_response(state, query, candidates, references)
