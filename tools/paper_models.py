"""Normalized paper-search tool input and output models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PaperSearchInput(BaseModel):
    query: str = Field(min_length=1)
    max_results: int = Field(default=5, ge=1, le=50)


class PaperRecord(BaseModel):
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    summary: str = ""
    pdf_url: str = ""
    entry_id: str = ""
    source: str


class PaperSearchOutput(BaseModel):
    papers: list[PaperRecord] = Field(default_factory=list)
