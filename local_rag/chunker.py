"""Dependency-free fixed-window baseline chunker."""

from local_rag.contracts import ParsedPage, TextChunk


class FixedWindowChunker:
    name = "fixed_window"
    version = "1.0"

    def __init__(self, chunk_size: int = 800, overlap: int = 120):
        if chunk_size < 1 or overlap < 0 or overlap >= chunk_size:
            raise ValueError("require chunk_size > overlap >= 0")
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, pages: list[ParsedPage]) -> list[TextChunk]:
        chunks: list[TextChunk] = []
        step = self.chunk_size - self.overlap
        for page in pages:
            text = page.text.strip()
            for start in range(0, len(text), step):
                end = min(start + self.chunk_size, len(text))
                if not text[start:end].strip():
                    continue
                chunks.append(TextChunk(
                    document_id=page.document_id,
                    chunk_id=f"{page.document_id}:p{page.page_number}:c{len(chunks) + 1}",
                    page_start=page.page_number,
                    page_end=page.page_number,
                    text=text[start:end],
                    char_start=start,
                    char_end=end,
                ))
                if end == len(text):
                    break
        return chunks
