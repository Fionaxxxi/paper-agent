from types import SimpleNamespace

import pymupdf
import pytest
from pydantic import ValidationError

from app.schemas import ChatRequest
from document_loader.pdf_loader import load_pdf_pages
from nodes import generate as generate_module


def _make_pdf(path):
    document = pymupdf.open()
    for number in (1, 2):
        page = document.new_page()
        page.insert_text((72, 72), f"Representative content on page {number}")
    document.save(path)
    document.close()


def test_selected_pdf_pages_extract_only_requested_text_and_render_png(tmp_path):
    pdf_path = tmp_path / "paper.pdf"
    _make_pdf(pdf_path)

    result = load_pdf_pages(str(pdf_path), [2], image_cache_dir=str(tmp_path / "cache"))

    assert result["success"] is True
    assert result["selected_pages"] == [2]
    assert result["page_count"] == 2
    assert "page 2" in result["text"]
    assert "page 1" not in result["text"]
    assert result["render_status"] == "rendered"
    assert len(result["image_paths"]) == 1
    assert result["image_paths"][0].endswith("page_2.png")


def test_selected_pdf_pages_reject_invalid_range_and_page_budget(tmp_path):
    pdf_path = tmp_path / "paper.pdf"
    _make_pdf(pdf_path)

    out_of_range = load_pdf_pages(str(pdf_path), [3], image_cache_dir=str(tmp_path / "cache"))
    over_budget = load_pdf_pages(str(pdf_path), [1, 2, 3, 4], max_pages=3, image_cache_dir=str(tmp_path / "cache"))

    assert out_of_range["success"] is False
    assert "超出范围" in out_of_range["error"]
    assert over_budget["success"] is False
    assert "最多分析 3 个" in over_budget["error"]
    with pytest.raises(ValidationError, match="pdf_path"):
        ChatRequest(query="分析第一页", pdf_pages=[1])
    with pytest.raises(ValidationError, match="正整数"):
        ChatRequest(query="分析页面", pdf_path="paper.pdf", pdf_pages=[0])


def test_pdf_vision_uses_separate_model_only_after_explicit_enable(monkeypatch, tmp_path):
    image_path = tmp_path / "page_1.png"
    image_path.write_bytes(b"representative-png-bytes")
    captured = {}

    class FakeLLM:
        def invoke(self, prompt):
            captured["prompt"] = prompt
            return SimpleNamespace(content="页面视觉分析", usage_metadata={"input_tokens": 20, "output_tokens": 5})

    def fake_get_llm(model_name=None):
        captured["model_name"] = model_name
        return FakeLLM()

    monkeypatch.setattr(generate_module.settings, "PDF_VISION_ENABLED", True)
    monkeypatch.setattr(generate_module.settings, "PDF_VISION_MODEL_NAME", "qwen-vl-max")
    monkeypatch.setattr(generate_module, "get_llm", fake_get_llm)

    result = generate_module.generate_node({
        "query": "分析第 1 页图表", "task_type": "pdf_reading", "pdf_path": "paper.pdf",
        "pdf_text": "=== PDF 第 1 页 ===\n图表说明", "pdf_page_count": 2,
        "pdf_selected_pages": [1], "pdf_page_images": [str(image_path)],
        "pdf_vision_status": "ready", "paper_metadata": {},
    })

    assert captured["model_name"] == "qwen-vl-max"
    assert captured["prompt"][0].content[1]["type"] == "image_url"
    assert result["pdf_vision_status"] == "used"
    assert result["paper_metadata"]["pdf_visual_page_count"] == 1
    assert result["token_usage"] == 25
