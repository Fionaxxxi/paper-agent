"""研究型论文检索的零 Token 查询规范化与约束处理。"""

from __future__ import annotations

import re
from typing import Any


YEAR_SINCE_PATTERN = re.compile(r"(?:自|从)?\s*((?:19|20)\d{2})\s*年?(?:以来|至今|之后|后)")
GENERIC_SEARCH_TERMS = {
    "architecture", "comparison", "contributions", "directions", "evaluation",
    "future", "large", "limitations", "methods", "models", "open", "overview",
    "paper", "papers", "problems", "recent", "research", "review", "study",
    "survey", "technology", "trend", "trends",
}
DOMAIN_REWRITES = (
    (("sft", "supervised fine-tuning", "supervised finetuning", "监督微调"),
     "SFT supervised fine-tuning large language models"),
    (("reflexion", "反思型agent", "反思型 agent"),
     "Reflexion reflective language agents verbal reinforcement learning"),
    (("instruction tuning", "指令微调"), "instruction tuning large language models"),
)


def extract_year_lower_bound(query: str) -> int | None:
    match = YEAR_SINCE_PATTERN.search(str(query or ""))
    return int(match.group(1)) if match else None


def normalized_research_topic(state: dict[str, Any]) -> str:
    raw_parts = [
        str(state.get("query") or ""),
        str(state.get("rewritten_query") or ""),
        str((state.get("research_analysis") or {}).get("topic") or ""),
    ]
    combined = " ".join(raw_parts).casefold()
    for aliases, rewrite in DOMAIN_REWRITES:
        if any(alias in combined for alias in aliases):
            return rewrite
    ascii_terms = re.findall(r"[A-Za-z][A-Za-z0-9+.-]*", " ".join(raw_parts))
    useful = [term for term in ascii_terms if term.casefold() not in GENERIC_SEARCH_TERMS]
    if useful:
        return " ".join(dict.fromkeys(useful))
    return str(state.get("rewritten_query") or state.get("query") or "").strip()


def build_research_search_query(state: dict[str, Any], objective: str = "") -> str:
    topic = normalized_research_topic(state)
    objective_text = str(objective or "").casefold()
    if any(term in objective_text for term in ("代表", "筛选", "landscape", "综述")):
        suffix = "survey review benchmark representative approaches"
    elif any(term in objective_text for term in ("比较", "对比", "优缺点", "适用", "技术路线")):
        suffix = "methods comparison evaluation benchmark"
    elif any(term in objective_text for term in ("空白", "局限", "挑战", "未来", "趋势")):
        suffix = "limitations challenges open problems future directions"
    else:
        suffix = "recent methods evaluation"
    return " ".join(dict.fromkeys(f"{topic} {suffix}".split()))


def filter_documents_by_year(documents: list[dict[str, Any]], query: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    lower_bound = extract_year_lower_bound(query)
    if lower_bound is None:
        return documents, {"enabled": False, "year_lower_bound": None, "removed_count": 0}
    kept = []
    removed = 0
    for document in documents:
        year = document.get("year")
        if isinstance(year, int) and year < lower_bound:
            removed += 1
            continue
        kept.append(document)
    return kept, {"enabled": True, "year_lower_bound": lower_bound, "removed_count": removed}


def core_topic_terms(state: dict[str, Any]) -> set[str]:
    topic = normalized_research_topic(state).casefold()
    return {
        term for term in re.findall(r"[a-z][a-z0-9+.-]*", topic)
        if len(term) > 2 and term not in GENERIC_SEARCH_TERMS
    }


def document_matches_topic(document: dict[str, Any], terms: set[str]) -> bool:
    if not terms:
        return False
    text = f"{document.get('title', '')} {document.get('content', '')}".casefold()
    tokens = set(re.findall(r"[a-z][a-z0-9+.-]*", text))
    if "sft" in terms:
        return "sft" in tokens or "supervised fine-tuning" in text
    return bool(terms & tokens)
