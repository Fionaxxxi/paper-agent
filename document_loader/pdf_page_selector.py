"""零 LLM 的 PDF 关键视觉页面选择器。"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from pypdf import PdfReader


VISUAL_INTENTS = {
    "chart": ("图表", "曲线", "折线", "柱状", "散点", "热力图", "趋势", "坐标轴", "误差带", "plot", "chart", "curve", "axis", "trend"),
    "table": ("表格", "实验结果", "指标", "消融", "数值", "table", "ablation", "benchmark result"),
    "figure": ("架构图", "流程图", "示意图", "模型图", "图中", "figure", "diagram", "pipeline", "architecture"),
    "formula": ("公式", "方程", "损失函数", "目标函数", "符号", "equation", "formula", "loss function"),
    "algorithm": ("算法", "伪代码", "步骤", "algorithm", "pseudocode"),
}

PAGE_MARKERS = {
    "chart": (r"\bfig(?:ure)?\.?\s*\d+", r"曲线|坐标轴|trend|plot|chart|accuracy|loss"),
    "table": (r"\btable\s*[ivx\d]+", r"表\s*\d+|ablation|benchmark|accuracy|f1|auc"),
    "figure": (r"\bfig(?:ure)?\.?\s*\d+", r"图\s*\d+|architecture|framework|pipeline|overview"),
    "formula": (r"\beq(?:uation)?\.?\s*\(?\d+", r"公式|loss|objective|where\s+[a-z]"),
    "algorithm": (r"\balgorithm\s*\d+", r"伪代码|input:|output:|procedure|for each"),
}


def detect_visual_intent(query: str) -> str:
    normalized = (query or "").lower()
    for intent, keywords in VISUAL_INTENTS.items():
        if any(keyword in normalized for keyword in keywords):
            return intent
    return ""


def select_visual_pages(
    pdf_path: str, query: str, *, max_pages: int = 3, max_scan_pages: int = 120
) -> dict[str, Any]:
    """根据查询意图与页面图注/关键词选择关键页，不发送文档或调用模型。"""
    intent = detect_visual_intent(query)
    if not intent:
        return {"enabled": False, "intent": "", "selected_pages": [], "candidates": [], "reason": "no_visual_intent"}
    path = Path(pdf_path)
    if not path.is_file() or path.suffix.lower() != ".pdf":
        return {"enabled": True, "intent": intent, "selected_pages": [], "candidates": [], "reason": "pdf_unavailable"}

    try:
        reader = PdfReader(str(path))
        patterns = tuple(re.compile(pattern, re.IGNORECASE) for pattern in PAGE_MARKERS[intent])
        query_terms = {term for term in re.findall(r"[a-z][a-z0-9_-]{2,}|[\u4e00-\u9fff]{2,}", query.lower())}
        candidates = []
        scanned_pages = min(len(reader.pages), max_scan_pages)
        for index, page in enumerate(reader.pages[:scanned_pages], 1):
            text = (page.extract_text() or "")[:8000]
            lowered = text.lower()
            marker_hits = sum(len(pattern.findall(text)) for pattern in patterns)
            query_hits = sum(1 for term in query_terms if term in lowered)
            caption_bonus = 3 if re.search(r"(?:figure|fig\.|table|algorithm|图|表)\s*[ivx\d一二三四五六七八九十]+", text, re.IGNORECASE) else 0
            score = marker_hits * 4 + query_hits * 2 + caption_bonus
            if score > 0:
                candidates.append({"page": index, "score": score, "marker_hits": marker_hits, "query_hits": query_hits})
        candidates.sort(key=lambda item: (-item["score"], item["page"]))
        selected = [item["page"] for item in candidates[:max_pages]]
        return {
            "enabled": True, "intent": intent, "selected_pages": selected,
            "candidates": candidates[:8],
            "scanned_page_count": scanned_pages,
            "scan_truncated": len(reader.pages) > scanned_pages,
            "reason": "caption_and_query_rank" if selected else "no_matching_page",
        }
    except Exception as error:
        return {
            "enabled": True, "intent": intent, "selected_pages": [], "candidates": [],
            "reason": "selection_failed", "error": f"{type(error).__name__}: {error}",
        }
