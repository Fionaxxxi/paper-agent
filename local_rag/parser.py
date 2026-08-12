"""Page-preserving PDF parser for local RAG experiments."""

from pathlib import Path

from pypdf import PdfReader

from local_rag.contracts import ParsedPage


class PyPDFPageParser:
    name = "pypdf_page"
    version = "1.0"

    def parse(self, path: Path, document_id: str) -> list[ParsedPage]:
        if not path.exists() or path.suffix.lower() != ".pdf":
            raise ValueError(f"invalid PDF path: {path}")
        reader = PdfReader(str(path))
        return [
            ParsedPage(document_id=document_id, page_number=index, text=(page.extract_text() or "").strip())
            for index, page in enumerate(reader.pages, start=1)
        ]
