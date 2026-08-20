from __future__ import annotations

from typing import Any, Dict, List, Tuple


PDF_SPECIALIST_SKILLS = {
    "figure_understanding",
    "table_analysis",
    "chart_analysis",
    "formula_explanation",
}
UNCERTAINTY_MARKERS = ("无法识别", "无法辨认", "不清晰", "不确定", "未定义", "unclear", "unknown")


def get_paper_metadata(result: Dict[str, Any]) -> Dict[str, Any]:
    """兼容现有离线评测入口。"""
    return result.get("paper_metadata", {})


def validate_pdf_reading_output(result: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """验证通用 PDFReadingSkill 的离线评测输出是否基本合格。"""
    errors: List[str] = []
    task_type = result.get("task_type")
    pdf_page_count = result.get("pdf_page_count", 0)
    answer = result.get("answer", "")
    metadata = get_paper_metadata(result)
    skill_used = metadata.get("skill_used", "")
    pdf_error = metadata.get("pdf_error", "")

    if task_type != "pdf_reading":
        errors.append(f"task_type expected=pdf_reading, actual={task_type}")
    if skill_used != "pdf_reading":
        errors.append(f"skill_used expected=pdf_reading, actual={skill_used}")
    if pdf_page_count <= 0:
        errors.append(f"pdf_page_count expected > 0, actual={pdf_page_count}")
    if pdf_error:
        errors.append(f"pdf_error is not empty: {pdf_error}")
    if not answer.strip():
        errors.append("pdf reading answer is empty")
    return len(errors) == 0, errors


def validate_pdf_grounding(state: dict[str, Any]) -> dict[str, Any]:
    metadata = state.get("paper_metadata", {})
    skill = metadata.get("skill_used", "")
    if state.get("task_type") != "pdf_reading" or skill not in PDF_SPECIALIST_SKILLS:
        return {
            "enabled": False,
            "status": "not_applicable",
            "passed": True,
            "checks": {},
            "failure_types": [],
            "issues": [],
        }

    answer = str(state.get("answer") or "")
    pages = list(state.get("pdf_selected_pages", []))
    vision_used = state.get("pdf_vision_status") in {"used", "ocr_only_degraded"}
    evidence = metadata.get("pdf_visual_evidence", {})
    evidence_text = str(evidence.get("text") or "").lower()
    uncertainty_required = any(marker in evidence_text for marker in UNCERTAINTY_MARKERS)

    page_reference = not pages or all(
        f"第 {page} 页" in answer or f"第{page}页" in answer
        for page in pages
    )
    if vision_used:
        evidence_mode = any(marker in answer for marker in ("OCR", "视觉", "图像证据", "页面图像"))
    else:
        evidence_mode = any(
            marker in answer
            for marker in ("仅依据文本", "仅依据图注", "提取文本", "未启用视觉", "未观察到图像")
        )
    uncertainty_disclosed = not uncertainty_required or any(
        marker in answer for marker in ("无法识别", "无法辨认", "不清晰", "不确定", "未定义", "无法确认")
    )

    checks = {
        "page_reference": page_reference,
        "evidence_mode": evidence_mode,
        "uncertainty_disclosed": uncertainty_disclosed,
    }
    messages = {
        "page_reference": "专项回答没有标明全部重点分析页码。",
        "evidence_mode": "专项回答没有说明使用的是视觉/OCR证据还是仅提取文本。",
        "uncertainty_disclosed": "OCR材料存在识别不确定性，但回答没有保留该限制。",
    }
    failures = [name for name, passed in checks.items() if not passed]
    return {
        "enabled": True,
        "status": "passed" if not failures else "failed",
        "passed": not failures,
        "skill": skill,
        "pages": pages,
        "vision_used": vision_used,
        "checks": checks,
        "failure_types": failures,
        "issues": [messages[name] for name in failures],
        "should_reflect": False,
    }
