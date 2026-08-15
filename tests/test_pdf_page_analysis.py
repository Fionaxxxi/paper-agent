from types import SimpleNamespace

import pymupdf
import pytest
from pydantic import ValidationError

from app.schemas import ChatRequest
from document_loader.pdf_loader import load_pdf_pages
from document_loader.pdf_visual_evidence import build_visual_evidence, normalize_ocr_text
from eval_harness import pdf_vision_smoke
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
    captured = {"models": [], "prompts": []}

    class FakeLLM:
        def __init__(self, content, input_tokens, output_tokens):
            self.content = content
            self.input_tokens = input_tokens
            self.output_tokens = output_tokens

        def invoke(self, prompt):
            captured["prompts"].append(prompt)
            return SimpleNamespace(content=self.content, usage_metadata={"input_tokens": self.input_tokens, "output_tokens": self.output_tokens})

    def fake_get_llm(model_name=None):
        captured["models"].append(model_name)
        return FakeLLM('{"answer":[{"text":"OCR页面文字"}]}', 20, 5) if model_name else FakeLLM("页面综合分析", 30, 10)

    monkeypatch.setattr(generate_module.settings, "PDF_VISION_ENABLED", True)
    monkeypatch.setattr(generate_module.settings, "PDF_VISION_MODEL_NAME", "qwen3.5-ocr")
    monkeypatch.setattr(generate_module.settings, "MODEL_NAME", "qwen3.7-max-2026-05-17")
    monkeypatch.setattr(generate_module, "get_llm", fake_get_llm)

    result = generate_module.generate_node({
        "query": "分析第 1 页图表", "task_type": "pdf_reading", "pdf_path": "paper.pdf",
        "pdf_text": "=== PDF 第 1 页 ===\n图表说明", "pdf_page_count": 2,
        "pdf_selected_pages": [1], "pdf_page_images": [str(image_path)],
        "pdf_vision_status": "ready", "paper_metadata": {},
    })

    assert captured["models"] == ["qwen3.5-ocr", None]
    assert captured["prompts"][0][0].content[1]["type"] == "image_url"
    assert "PDF 页面 OCR 结果" in captured["prompts"][1]
    assert result["answer"] == "页面综合分析"
    assert result["pdf_vision_status"] == "used"
    assert result["paper_metadata"]["pdf_visual_page_count"] == 1
    assert result["paper_metadata"]["pdf_ocr_model"] == "qwen3.5-ocr"
    assert result["paper_metadata"]["pdf_synthesis_model"] == "qwen3.7-max-2026-05-17"
    assert result["paper_metadata"]["pdf_visual_evidence"] == {
        "source_file": "paper.pdf", "pages": [1], "model": "qwen3.5-ocr",
        "content_types": ["text"], "character_count": 7, "text": "OCR页面文字",
    }
    assert result["llm_call_count"] == 2
    assert result["token_usage"] == 65


def test_pdf_vision_preserves_ocr_when_main_synthesis_fails(monkeypatch, tmp_path):
    image_path = tmp_path / "page_1.png"
    image_path.write_bytes(b"representative-png-bytes")
    calls = []

    class FakeLLM:
        def __init__(self, model_name):
            self.model_name = model_name

        def invoke(self, prompt):
            calls.append(self.model_name)
            if self.model_name == "qwen3.5-ocr":
                return SimpleNamespace(
                    content='{"answer":[{"text":"OCR保留内容"}]}',
                    usage_metadata={"input_tokens": 20, "output_tokens": 5},
                )
            raise RuntimeError("synthesis unavailable")

    monkeypatch.setattr(generate_module.settings, "PDF_VISION_ENABLED", True)
    monkeypatch.setattr(generate_module.settings, "PDF_VISION_MODEL_NAME", "qwen3.5-ocr")
    monkeypatch.setattr(generate_module.settings, "MODEL_NAME", "qwen3.7-max-2026-05-17")
    monkeypatch.setattr(generate_module, "get_llm", lambda model_name=None: FakeLLM(model_name or "qwen3.7-max-2026-05-17"))

    result = generate_module.generate_node({
        "query": "分析第 1 页", "task_type": "pdf_reading", "pdf_path": "paper.pdf",
        "pdf_text": "=== PDF 第 1 页 ===\n正文", "pdf_page_count": 1,
        "pdf_selected_pages": [1], "pdf_page_images": [str(image_path)],
        "pdf_vision_status": "ready", "paper_metadata": {},
    })

    assert calls == ["qwen3.5-ocr", "qwen3.7-max-2026-05-17"]
    assert result["pdf_vision_status"] == "ocr_only_degraded"
    assert "OCR保留内容" in result["answer"]
    assert "研究综合暂不可用" in result["answer"]
    assert result["paper_metadata"]["pdf_ocr_model"] == "qwen3.5-ocr"
    assert result["paper_metadata"]["pdf_synthesis_model"] == "qwen3.7-max-2026-05-17"
    assert result["llm_call_count"] == 2
    assert result["token_usage"] == 25


def test_pdf_vision_smoke_requires_explicit_online_confirmation(monkeypatch):
    monkeypatch.setattr("sys.argv", ["pdf_vision_smoke"])

    with pytest.raises(SystemExit) as error:
        pdf_vision_smoke.main()

    assert error.value.code == 2


def test_pdf_visual_evidence_normalizes_json_and_hides_absolute_path():
    raw = '{"answer":[{"text":"Figure 1 agent flow"},{"text":"Table 2 results"},{"formula":"L = x + y"}]}'

    evidence = build_visual_evidence(
        raw, pdf_path=r"D:\\private\\papers\\agent.pdf", selected_pages=[3], model_name="qwen3.5-ocr"
    )

    assert normalize_ocr_text(raw) == "Figure 1 agent flow\nTable 2 results\nL = x + y"
    assert evidence["source_file"] == "agent.pdf"
    assert evidence["pages"] == [3]
    assert set(evidence["content_types"]) == {"figure", "table", "formula"}
    assert "D:\\private" not in str(evidence)
