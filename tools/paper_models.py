"""Normalized paper-search tool input and output models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PaperSearchInput(BaseModel):
    query: str = Field(min_length=1)
    max_results: int = Field(default=5, ge=1, le=50)


class PaperLookupInput(BaseModel):
    identity: str = Field(min_length=1, max_length=200)


class PaperRecord(BaseModel):
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    summary: str = ""
    pdf_url: str = ""
    entry_id: str = ""
    doi: str = ""
    cited_by_count: int = Field(default=0, ge=0)
    landing_page_url: str = ""
    source: str


class PaperSearchOutput(BaseModel):
    papers: list[PaperRecord] = Field(default_factory=list)


class PaperLookupOutput(BaseModel):
    paper: PaperRecord | None = None
