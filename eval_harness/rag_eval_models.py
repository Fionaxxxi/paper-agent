"""Technology-neutral contracts for local RAG evaluation datasets."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field, model_validator


class EvidenceSpan(BaseModel):
    document_id: str = Field(min_length=1)
    chunk_id: str = Field(min_length=1)
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)
    quote: str = Field(min_length=1)
    source_path: str = Field(min_length=1)
    relevance_grade: int = Field(default=3, ge=1, le=3)

    @model_validator(mode="after")
    def validate_pages(self):
        if self.page_end < self.page_start:
            raise ValueError("page_end must not be before page_start")
        return self


class RAGEvalCase(BaseModel):
    id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    language: str
    category: str
    difficulty: str
    reference_answer: str = Field(min_length=1)
    evidence: list[EvidenceSpan] = Field(min_length=1)


class RAGEvalDataset(BaseModel):
    dataset_name: str = Field(min_length=1)
    dataset_version: str = Field(min_length=1)
    description: str
    corpus_version: str = Field(min_length=1)
    k_values: list[int] = Field(default_factory=lambda: [1, 3, 5])
    cases: list[RAGEvalCase] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_invariants(self):
        if any(k < 1 for k in self.k_values) or len(self.k_values) != len(set(self.k_values)):
            raise ValueError("k_values must be unique positive integers")
        ids = [case.id for case in self.cases]
        if len(ids) != len(set(ids)):
            raise ValueError("case ids must be unique")
        for case in self.cases:
            evidence_ids = [(span.document_id, span.chunk_id) for span in case.evidence]
            if len(evidence_ids) != len(set(evidence_ids)):
                raise ValueError("evidence document_id/chunk_id pairs must be unique within a case")
        return self


class RAGExperimentConfig(BaseModel):
    config_id: str = Field(min_length=1)
    retriever_family: str = Field(min_length=1)
    parser: str = Field(min_length=1)
    chunker: str = Field(min_length=1)
    embedding: str = Field(min_length=1)
    store: str = Field(min_length=1)
    reranker: str = "none"
    graph_retriever: str = "none"
    parameters: dict = Field(default_factory=dict)


def load_rag_dataset(path: Path) -> RAGEvalDataset:
    return RAGEvalDataset.model_validate(json.loads(path.read_text(encoding="utf-8")))
