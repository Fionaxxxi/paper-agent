"""统一检索范围路由：只选择已实现后端，未实现能力显式降级。"""

from __future__ import annotations

from typing import Any

from core.config import settings

PERSONAL_SIGNALS = ("我的论文", "我的收藏", "个人论文库", "zotero", "我收藏的")
LOCAL_SIGNALS = ("本地知识库", "已有论文", "本地论文", "已下载论文")
ONLINE_SIGNALS = ("最新", "最近", "今年", "当前", "新论文", "2025", "2026")
HYBRID_SIGNALS = ("结合我", "结合本地", "结合已有", "以及最新", "和最近")
MEMORY_SIGNALS = ("基于之前", "继续上次", "上次结论", "之前总结")


def select_retrieval_strategy(state: dict[str, Any]) -> dict[str, Any]:
    query = str(state.get("query") or "").casefold()
    configured = settings.RETRIEVAL_MODE.casefold()
    requested_scope = str(state.get("retrieval_scope") or "auto").casefold()
    if state.get("pdf_path"):
        return {"mode": "pdf", "sources": ["pdf"], "reason": "uploaded_pdf", "fallback": "none"}
    if requested_scope == "online":
        return {"mode": "online", "sources": ["arxiv"], "reason": "user_selected_online", "fallback": "local_for_comparison_gap"}
    if requested_scope == "personal":
        if state.get("user_id"):
            return {"mode": "personal", "sources": ["personal_library"], "reason": "user_selected_personal", "fallback": "none"}
        return {"mode": "unavailable", "sources": [], "reason": "authentication_required", "requested_scope": "personal", "fallback": "none"}
    if requested_scope == "hybrid":
        if state.get("user_id"):
            return {"mode": "hybrid", "sources": ["personal_library", "arxiv"], "reason": "user_selected_private_public", "fallback": "online"}
        return {"mode": "unavailable", "sources": [], "reason": "authentication_required", "requested_scope": "hybrid", "fallback": "none"}
    if any(signal in query for signal in HYBRID_SIGNALS):
        sources = ["personal_library", "arxiv"] if state.get("user_id") else ["local_rag", "arxiv"]
        return {"mode": "hybrid", "sources": sources, "reason": "private_public_combination", "fallback": "online"}
    if any(signal in query for signal in MEMORY_SIGNALS):
        return {
            "mode": "online", "sources": ["arxiv"],
            "reason": "memory_augmented_research", "fallback": "local_for_comparison_gap",
            "requested_scope": "memory",
        }
    if any(signal in query for signal in PERSONAL_SIGNALS):
        if state.get("user_id"):
            return {"mode": "personal", "sources": ["personal_library"], "reason": "authenticated_personal_library", "fallback": "none"}
        if configured == "zotero" and settings.ZOTERO_LIBRARY_ID:
            return {"mode": "personal", "sources": ["zotero"], "reason": "personal_library_requested", "fallback": "none"}
        return {
            "mode": "unavailable", "sources": [],
            "reason": "personal_library_not_configured", "fallback": "none",
            "requested_scope": "personal",
        }
    if configured == "local_rag" or any(signal in query for signal in LOCAL_SIGNALS):
        return {"mode": "local", "sources": ["local_rag"], "reason": "local_scope_requested", "fallback": "online"}
    if configured == "zotero":
        return {"mode": "personal", "sources": ["zotero"], "reason": "configured_personal_provider", "fallback": "none"}
    online_sources = ["arxiv", "openalex"] if configured in {"multi", "multi_source"} else [configured if configured in {"arxiv", "openalex", "mcp_catalog"} else "arxiv"]
    return {
        "mode": "online", "sources": online_sources,
        "reason": "freshness_requested" if any(signal in query for signal in ONLINE_SIGNALS) else "default_online",
        "fallback": "local_for_comparison_gap",
    }
