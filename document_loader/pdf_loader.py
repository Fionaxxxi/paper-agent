import hashlib
from pathlib import Path
from typing import Dict, Any

from pypdf import PdfReader


def load_pdf_pages(
    pdf_path: str,
    pages: list[int],
    *,
    max_chars: int = 12000,
    max_pages: int = 3,
    image_cache_dir: str = "data/cache/pdf_pages",
) -> Dict[str, Any]:
    """提取并渲染用户明确指定的 1-based PDF 页面。"""
    path = Path(pdf_path)
    if not path.is_file():
        return {"success": False, "text": "", "page_count": 0, "selected_pages": [], "image_paths": [], "render_status": "failed", "error": f"PDF 文件不存在：{pdf_path}"}
    if path.suffix.lower() != ".pdf":
        return {"success": False, "text": "", "page_count": 0, "selected_pages": [], "image_paths": [], "render_status": "failed", "error": "当前文件不是 PDF 格式"}
    selected = list(dict.fromkeys(pages))
    if not selected:
        return load_pdf_text(pdf_path, max_chars=max_chars)
    if len(selected) > max_pages:
        return {"success": False, "text": "", "page_count": 0, "selected_pages": [], "image_paths": [], "render_status": "failed", "error": f"一次最多分析 {max_pages} 个 PDF 页面"}
    if any(not isinstance(page, int) or isinstance(page, bool) or page < 1 for page in selected):
        return {"success": False, "text": "", "page_count": 0, "selected_pages": [], "image_paths": [], "render_status": "failed", "error": "PDF 页码必须是从 1 开始的正整数"}

    try:
        reader = PdfReader(str(path))
        page_count = len(reader.pages)
        invalid = [page for page in selected if page > page_count]
        if invalid:
            return {"success": False, "text": "", "page_count": page_count, "selected_pages": selected, "image_paths": [], "render_status": "failed", "error": f"PDF 页码超出范围：{invalid}，文档共 {page_count} 页"}
        sections = []
        for page_number in selected:
            text = reader.pages[page_number - 1].extract_text() or ""
            sections.append(f"=== PDF 第 {page_number} 页 ===\n{text.strip() or '[该页没有可提取文本]'}")
        selected_text = "\n\n".join(sections)
        if len(selected_text) > max_chars:
            selected_text = selected_text[:max_chars] + "\n\n...[指定页面文本已截断]"

        image_paths: list[str] = []
        render_status = "renderer_unavailable"
        try:
            import pymupdf

            fingerprint = hashlib.sha256(f"{path.resolve()}|{path.stat().st_mtime_ns}".encode()).hexdigest()[:16]
            output_dir = Path(image_cache_dir) / fingerprint
            output_dir.mkdir(parents=True, exist_ok=True)
            document = pymupdf.open(str(path))
            try:
                for page_number in selected:
                    output = output_dir / f"page_{page_number}.png"
                    if not output.exists():
                        document.load_page(page_number - 1).get_pixmap(dpi=144, alpha=False).save(str(output))
                    image_paths.append(str(output.resolve()))
            finally:
                document.close()
            render_status = "rendered"
        except (ImportError, OSError, RuntimeError, ValueError):
            image_paths = []

        return {"success": True, "text": selected_text, "page_count": page_count, "selected_pages": selected, "image_paths": image_paths, "render_status": render_status, "error": ""}
    except Exception as error:
        return {"success": False, "text": "", "page_count": 0, "selected_pages": selected, "image_paths": [], "render_status": "failed", "error": f"PDF 指定页面读取失败：{type(error).__name__}: {error}"}


def load_pdf_text(pdf_path: str, max_chars: int = 12000) -> Dict[str, Any]:
    """
    读取本地 PDF 文件文本。

    第一版只做文本提取，不做 OCR 和图表识别。
    max_chars 用于限制传入 LLM 的文本长度，避免 prompt 过长。
    """

    path = Path(pdf_path)

    if not path.exists():
        return {
            "success": False,
            "text": "",
            "page_count": 0,
            "error": f"PDF 文件不存在：{pdf_path}",
        }

    if path.suffix.lower() != ".pdf":
        return {
            "success": False,
            "text": "",
            "page_count": 0,
            "error": "当前文件不是 PDF 格式",
        }

    try:
        reader = PdfReader(str(path))
        pages_text = []

        for page in reader.pages:
            text = page.extract_text() or ""
            if text.strip():
                pages_text.append(text.strip())

        full_text = "\n\n".join(pages_text)

        if len(full_text) > max_chars:
            full_text = full_text[:max_chars] + "\n\n...[PDF 内容已截断]"

        return {
            "success": True,
            "text": full_text,
            "page_count": len(reader.pages),
            "error": "",
        }

    except Exception as e:
        return {
            "success": False,
            "text": "",
            "page_count": 0,
            "error": f"PDF 读取失败：{type(e).__name__}: {e}",
        }
