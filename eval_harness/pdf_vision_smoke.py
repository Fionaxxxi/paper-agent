"""单案例在线 PDF 页面 OCR 冒烟；必须显式确认才会调用模型。"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from core.config import settings
from document_loader.pdf_loader import load_pdf_pages
from nodes.generate import generate_node
from validators.pdf_grounding_validator import validate_pdf_grounding


DEFAULT_PDF = Path("data/papers/2404.16130_graph_rag.pdf")


def main() -> int:
    parser = argparse.ArgumentParser(description="运行一次 qwen3.5-ocr PDF 页面在线冒烟")
    parser.add_argument("--confirm-online", action="store_true", help="确认发送指定页面并产生OCR与综合两次在线模型调用")
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    parser.add_argument("--page", type=int, default=4)
    parser.add_argument("--output", type=Path, default=Path("outputs/pdf_vision_smoke/latest.json"))
    args = parser.parse_args()
    if not args.confirm_online:
        parser.error("在线调用被保护；请显式添加 --confirm-online")
    if not settings.OPENAI_API_KEY:
        raise SystemExit("缺少 OPENAI_API_KEY，未执行在线调用")

    loaded = load_pdf_pages(str(args.pdf), [args.page], max_chars=settings.PDF_MAX_CHARS, max_pages=1, image_cache_dir=settings.PDF_PAGE_IMAGE_CACHE_DIR)
    if not loaded.get("success") or not loaded.get("image_paths"):
        raise SystemExit(f"指定页面准备失败：{loaded.get('error') or loaded.get('render_status')}")

    previous_enabled = settings.PDF_VISION_ENABLED
    settings.PDF_VISION_ENABLED = True
    started = time.perf_counter()
    request_state = {
        "query": f"解释第{args.page}页的架构图或流程图：说明组件、输入输出和关系；无法识别的内容要明确说明。",
        "task_type": "pdf_reading", "pdf_path": args.pdf.name,
        "pdf_text": loaded["text"], "pdf_page_count": loaded["page_count"],
        "pdf_selected_pages": loaded["selected_pages"], "pdf_page_images": loaded["image_paths"],
        "pdf_vision_status": "ready", "paper_metadata": {}, "llm_usage": [],
    }
    try:
        result = generate_node(request_state)
    finally:
        settings.PDF_VISION_ENABLED = previous_enabled

    answer = result.get("answer", "")
    metadata = result.get("paper_metadata", {})
    structured = metadata.get("pdf_structured_output", {})
    grounding = validate_pdf_grounding({**request_state, **result})
    report = {
        "success": (
            result.get("pdf_vision_status") == "used"
            and not result.get("error_message")
            and structured.get("valid") is True
            and grounding.get("passed") is True
        ),
        "model": result.get("paper_metadata", {}).get("pdf_vision_model", settings.PDF_VISION_MODEL_NAME),
        "ocr_model": result.get("paper_metadata", {}).get("pdf_ocr_model", settings.PDF_VISION_MODEL_NAME),
        "synthesis_model": result.get("paper_metadata", {}).get("pdf_synthesis_model", settings.MODEL_NAME),
        "paper": args.pdf.name, "page": args.page,
        "pdf_vision_status": result.get("pdf_vision_status", "failed"),
        "visual_page_count": result.get("paper_metadata", {}).get("pdf_visual_page_count", 0),
        "skill_used": metadata.get("skill_used", ""),
        "structured_output_status": structured.get("status", "not_applicable"),
        "structured_output_schema": structured.get("schema", ""),
        "structured_output_error": structured.get("error", ""),
        "grounding_status": grounding.get("status", "not_applicable"),
        "input_tokens": result.get("input_token_usage", 0), "output_tokens": result.get("output_token_usage", 0),
        "total_tokens": result.get("token_usage", 0),
        "llm_call_count": result.get("llm_call_count", 0),
        "duration_seconds": round(time.perf_counter() - started, 3),
        "answer_excerpt": str(answer)[:500],
        "error_type": (result.get("error_message") or "").split(":", 1)[0],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"Report: {args.output.resolve()}")
    return 0 if report["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
