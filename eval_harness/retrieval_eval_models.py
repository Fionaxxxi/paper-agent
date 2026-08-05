"""Validated schemas for versioned online retrieval evaluation datasets."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field, model_validator


class RelevantPaper(BaseModel):
    title: str = Field(min_length=1)
    arxiv_id: str = ""
    doi: str = ""
    relevance_grade: int = Field(default=3, ge=1, le=3)
    dimensions: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_stable_identity(self):
        if not self.arxiv_id and not self.doi and not self.title:
            raise ValueError("a relevant paper needs at least one stable identity")
        return self


class RetrievalEvalCase(BaseModel):
    id: str = Field(min_length=1)
    query: str = Field(min_length=1)
    language: str
    category: str
    difficulty: str
    expected_dimensions: list[str] = Field(default_factory=list)
    relevant_papers: list[RelevantPaper] = Field(min_length=1)


class RetrievalEvalDataset(BaseModel):
    dataset_name: str
    dataset_version: str
    description: str
    k_values: list[int] = Field(default_factory=lambda: [1, 3, 5])
    cases: list[RetrievalEvalCase] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_dataset_invariants(self):
        if any(k < 1 for k in self.k_values):
            raise ValueError("all k_values must be positive")
        if len(self.k_values) != len(set(self.k_values)):
            raise ValueError("k_values must not contain duplicates")
        case_ids = [case.id for case in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("case ids must be unique")
        return self


def load_retrieval_dataset(path: Path) -> RetrievalEvalDataset:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return RetrievalEvalDataset.model_validate(payload)
