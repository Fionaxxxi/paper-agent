"""Technology-neutral parser and chunker contracts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class ParsedPage:
    document_id: str
    page_number: int
    text: str


@dataclass(frozen=True)
class TextChunk:
    document_id: str
    chunk_id: str
    page_start: int
    page_end: int
    text: str
    char_start: int
    char_end: int


class DocumentParser(Protocol):
    name: str
    version: str

    def parse(self, path: Path, document_id: str) -> list[ParsedPage]: ...


class DocumentChunker(Protocol):
    name: str
    version: str

    def chunk(self, pages: list[ParsedPage]) -> list[TextChunk]: ...
