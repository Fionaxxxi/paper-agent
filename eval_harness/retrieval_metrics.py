"""Deterministic ranking metrics for paper retrieval evaluation."""

from __future__ import annotations

import math
import re
from typing import Any

from eval_harness.retrieval_eval_models import RelevantPaper, RetrievalEvalCase


ARXIV_ID_PATTERN = re.compile(r"(?<!\d)(\d{4}\.\d{4,5})(?:v\d+)?(?!\d)")


def normalize_doi(value: str) -> str:
    normalized = (value or "").strip().casefold()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):]
    return normalized


def normalize_title(value: str) -> str:
    normalized = re.sub(r"[^\w]+", " ", (value or "").casefold())
    return " ".join(normalized.split())


def extract_arxiv_id(*values: str) -> str:
    for value in values:
        match = ARXIV_ID_PATTERN.search(value or "")
        if match:
            return match.group(1)
    return ""


def paper_identity_keys(paper: dict[str, Any] | RelevantPaper) -> set[str]:
    if isinstance(paper, RelevantPaper):
        title = paper.title
        doi = paper.doi
        arxiv_id = paper.arxiv_id
        entry_id = ""
        pdf_url = ""
    else:
        title = str(paper.get("title") or "")
        doi = str(paper.get("doi") or "")
        arxiv_id = str(paper.get("arxiv_id") or "")
        entry_id = str(paper.get("entry_id") or "")
        pdf_url = str(paper.get("pdf_url") or "")

    keys = set()
    normalized_doi = normalize_doi(doi)
    if normalized_doi:
        keys.add(f"doi:{normalized_doi}")
    normalized_arxiv_id = extract_arxiv_id(arxiv_id, entry_id, pdf_url, doi)
    if normalized_arxiv_id:
        keys.add(f"arxiv:{normalized_arxiv_id}")
    normalized_title = normalize_title(title)
    if normalized_title:
        keys.add(f"title:{normalized_title}")
    return keys


def match_relevant_paper(
    paper: dict[str, Any],
    relevant_papers: list[RelevantPaper],
) -> tuple[int | None, int]:
    candidate_keys = paper_identity_keys(paper)
    for index, relevant in enumerate(relevant_papers):
        if candidate_keys & paper_identity_keys(relevant):
            return index, relevant.relevance_grade
    return None, 0


def _dcg(grades: list[int]) -> float:
    return sum(
        (2**grade - 1) / math.log2(rank + 2)
        for rank, grade in enumerate(grades)
    )


def calculate_case_metrics(
    case: RetrievalEvalCase,
    papers: list[dict[str, Any]],
    k_values: list[int],
) -> dict[str, Any]:
    matched_gold_indexes = []
    grades = []
    matched_dimensions = set()

    for paper in papers:
        gold_index, grade = match_relevant_paper(paper, case.relevant_papers)
        grades.append(grade)
        matched_gold_indexes.append(gold_index)
        if gold_index is not None:
            matched_dimensions.update(case.relevant_papers[gold_index].dimensions)

    metrics: dict[str, Any] = {}
    gold_count = len(case.relevant_papers)
    ideal_grades = sorted(
        (paper.relevance_grade for paper in case.relevant_papers),
        reverse=True,
    )

    for k in sorted(k_values):
        top_indexes = matched_gold_indexes[:k]
        unique_relevant = {index for index in top_indexes if index is not None}
        relevant_count = sum(index is not None for index in top_indexes)
        metrics[f"recall_at_{k}"] = round(len(unique_relevant) / gold_count, 6)
        metrics[f"precision_at_{k}"] = round(relevant_count / k, 6)

        first_rank = next(
            (rank for rank, index in enumerate(top_indexes, start=1) if index is not None),
            None,
        )
        metrics[f"mrr_at_{k}"] = round(1 / first_rank, 6) if first_rank else 0.0

        actual_dcg = _dcg(grades[:k])
        ideal_dcg = _dcg(ideal_grades[:k])
        metrics[f"ndcg_at_{k}"] = (
            round(actual_dcg / ideal_dcg, 6) if ideal_dcg else 0.0
        )

    expected_dimensions = set(case.expected_dimensions)
    metrics["dimension_coverage_pct"] = (
        round(len(matched_dimensions & expected_dimensions) / len(expected_dimensions) * 100, 2)
        if expected_dimensions
        else 100.0
    )
    metrics["matched_relevant_count"] = len(
        {index for index in matched_gold_indexes if index is not None}
    )
    metrics["first_relevant_rank"] = next(
        (rank for rank, index in enumerate(matched_gold_indexes, start=1) if index is not None),
        0,
    )
    metrics["returned_count"] = len(papers)
    return metrics


def duplicate_rate(raw_count: int, merged_count: int) -> float:
    if raw_count <= 0:
        return 0.0
    duplicates = max(raw_count - merged_count, 0)
    return round(duplicates / raw_count * 100, 2)
