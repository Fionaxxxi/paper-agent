from pathlib import Path
from typing import Dict, Any

from pypdf import PdfReader


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