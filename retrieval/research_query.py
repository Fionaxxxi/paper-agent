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
    (("prompt cache", "prompt caching", "提示词缓存"),
     "LLM prompt caching automatic prefix caching KV cache inference serving agent systems"),
    (("harness engineering", "agent harness", "harness工程", "harness 工程"),
     "LLM agent harness engineering scaffolding runtime infrastructure workflow orchestration evaluation"),
    (("aigc", "ai generated content", "ai-generated content", "人工智能生成内容"),
     "AIGC artificial intelligence generated content generative AI content generation"),
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
    if "prompt cach" in topic.casefold() or "prefix cach" in topic.casefold():
        if any(term in objective_text for term in ("界定", "定义", "区别", "代表论文")):
            suffix = "prompt cache survey prefix reuse inference performance benchmarks"
        elif any(term in objective_text for term in ("机制", "原理", "实现", "kv", "prefix")):
            suffix = "automatic prefix caching radix tree KV cache serving architecture"
        elif any(term in objective_text for term in ("agent", "开发", "使用", "工程", "成本")):
            suffix = "agent context engineering repeated prefix latency cost optimization"
        else:
            suffix = "prompt caching inference serving systems"
    elif "harness" in topic.casefold():
        if any(term in objective_text for term in ("边界", "workflow", "协作", "编排")):
            suffix = "agent workflow orchestration state machine task graph execution pipeline"
        elif any(term in objective_text for term in ("评测", "沙箱", "工具", "可观测", "失败")):
            suffix = "agent evaluation harness tool sandbox observability policy failure recovery"
        else:
            suffix = "agent harness scaffolding runtime infrastructure engineering architecture"
    elif "aigc" in topic.casefold() or "artificial intelligence generated content" in topic.casefold():
        if any(term in objective_text for term in ("安全", "风险", "检测", "版权", "评测")):
            suffix = "AI-generated content evaluation safety detection watermarking provenance"
        elif any(term in objective_text for term in ("方向", "应用", "场景", "多模态")):
            suffix = "text image video multimodal generative models applications survey"
        else:
            suffix = "survey foundation models representative methods benchmarks"
    elif any(term in objective_text for term in ("代表", "筛选", "landscape", "综述")):
        suffix = "survey review benchmark representative approaches"
    elif any(term in objective_text for term in ("比较", "对比", "优缺点", "适用", "技术路线")):
        suffix = "methods comparison evaluation benchmark"
    elif any(term in objective_text for term in ("空白", "局限", "挑战", "未来", "趋势", "方向", "应用", "场景")):
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


def required_topic_groups(state: dict[str, Any]) -> dict[str, tuple[str, ...]]:
    """Return hard semantic coverage groups for ambiguity-prone engineering terms."""
    combined = " ".join((
        str(state.get("query") or ""),
        str(state.get("rewritten_query") or ""),
        str((state.get("research_analysis") or {}).get("topic") or ""),
    )).casefold()
    if "harness" not in combined:
        if "prompt cache" in combined or "prompt caching" in combined or "prefix caching" in combined:
            return {
                "prompt_cache": (
                    "prompt cache", "prompt caching", "prefix cache", "prefix caching",
                    "automatic prefix caching", "shared prefix", "context caching",
                )
            }
        return {}
    groups = {
        "agent": ("agent", "language agent", "llm agent"),
        "harness": (
            "harness", "scaffolding", "agent runtime", "runtime infrastructure",
            "evaluation infrastructure", "evaluation framework", "tool sandbox",
        ),
    }
    if "workflow" in combined or "流程" in combined or "orchestration" in combined:
        groups["workflow"] = (
            "workflow", "orchestration", "state machine", "execution graph",
            "task graph", "pipeline",
        )
    return groups


def topic_group_coverage(
    documents: list[dict[str, Any]], groups: dict[str, tuple[str, ...]]
) -> dict[str, Any]:
    covered = []
    for name, aliases in groups.items():
        if any(
            any(alias in f"{doc.get('title', '')} {doc.get('content', '')}".casefold() for alias in aliases)
            for doc in documents
        ):
            covered.append(name)
    missing = [name for name in groups if name not in covered]
    return {
        "enabled": bool(groups), "required_groups": list(groups),
        "covered_groups": covered, "missing_groups": missing,
        "coverage_pct": round(len(covered) / len(groups) * 100, 2) if groups else 0.0,
        "passed": bool(groups) and not missing,
    }
