import json
from pathlib import Path
from typing import Any


CONTENT_MARKERS = {
    "table": ("table", "表格", "row", "column"),
    "formula": ("formula", "equation", "公式", "latex"),
    "figure": ("figure", "fig.", "图 ", "图注", "caption"),
}


def _extract_text(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            result.extend(_extract_text(item))
        return result
    if isinstance(value, dict):
        result: list[str] = []
        for key, item in value.items():
            if key.lower() in {"text", "content", "caption", "formula", "markdown", "answer"}:
                result.extend(_extract_text(item))
            elif isinstance(item, (dict, list)):
                result.extend(_extract_text(item))
        return result
    return []


def normalize_ocr_text(raw_output: str) -> str:
    """把 OCR 的 JSON/纯文本输出统一成可供主模型阅读的文本。"""
    raw_output = (raw_output or "").strip()
    if not raw_output:
        return ""
    try:
        parsed = json.loads(raw_output)
    except json.JSONDecodeError:
        return raw_output
    extracted = _extract_text(parsed)
    return "\n".join(dict.fromkeys(extracted)) or raw_output


def build_visual_evidence(
    raw_output: str,
    *,
    pdf_path: str,
    selected_pages: list[int],
    model_name: str,
    task: str = "pdf_reading",
    page_selection: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """生成不含本地绝对路径的、可审计的页面 OCR 证据摘要。"""
    normalized = normalize_ocr_text(raw_output)
    lowered = f"{raw_output}\n{normalized}".lower()
    content_types = [
        content_type
        for content_type, markers in CONTENT_MARKERS.items()
        if any(marker in lowered for marker in markers)
    ]
    if normalized and not content_types:
        content_types = ["text"]
    return {
        "source_file": Path(pdf_path).name,
        "pages": list(selected_pages),
        "model": model_name,
        "analysis_mode": "query_aware_page_vision_v2",
        "task": task,
        "page_selection": page_selection or {"enabled": False, "reason": "manual_pages"},
        "content_types": content_types,
        "character_count": len(normalized),
        "text": normalized,
    }


def format_visual_evidence_for_prompt(evidence: dict[str, Any]) -> str:
    pages = "、".join(f"第 {page} 页" for page in evidence.get("pages", [])) or "未知页"
    types = ", ".join(evidence.get("content_types", [])) or "unknown"
    return (
        f"来源文件：{evidence.get('source_file', '')}\n"
        f"来源页码：{pages}\n"
        f"识别内容类型：{types}\n"
        f"OCR 模型：{evidence.get('model', '')}\n\n"
        f"视觉任务：{evidence.get('task', 'pdf_reading')}\n"
        f"{evidence.get('text', '')}"
    )
