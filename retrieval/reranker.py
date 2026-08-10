"""Deterministic, zero-token reranking for multi-source paper candidates."""

from __future__ import annotations

import math
import re
from typing import Any, Dict, List

from retrieval.result_merger import build_document_keys, normalize_text


TOKEN_PATTERN = re.compile(r"[a-z0-9]+|[\u4e00-\u9fff]", re.IGNORECASE)
ARXIV_ID_PATTERN = re.compile(r"(?<!\d)(\d{4}\.\d{4,5})(?:v\d+)?(?!\d)")
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "in", "is", "of", "on", "or", "that", "the", "to", "using", "with",
    "what", "why", "how", "paper", "papers", "research", "study",
}


def tokenize(value: Any) -> set[str]:
    """Return stable English tokens and individual CJK characters."""

    return {
        token.casefold()
        for token in TOKEN_PATTERN.findall(str(value or ""))
        if token.casefold() not in STOPWORDS
    }


def _extract_arxiv_ids(document: Dict[str, Any]) -> set[str]:
    values = (
        document.get("doi", ""),
        document.get("entry_id", ""),
        document.get("pdf_url", ""),
        document.get("landing_page_url", ""),
    )
    return {
        match.group(1)
        for value in values
        for match in ARXIV_ID_PATTERN.finditer(str(value or ""))
    }


def verify_document_metadata(document: Dict[str, Any]) -> Dict[str, Any]:
    """Check locally provable metadata consistency without external calls."""

    warnings: list[str] = []
    if not str(document.get("title") or "").strip():
        warnings.append("MISSING_TITLE")
    if not str(document.get("doi") or document.get("entry_id") or "").strip():
        warnings.append("MISSING_STABLE_IDENTITY")
    if not str(document.get("content") or document.get("summary") or "").strip():
        warnings.append("MISSING_ABSTRACT")
    if len(_extract_arxiv_ids(document)) > 1:
        warnings.append("ARXIV_ID_CONFLICT")

    year = document.get("year")
    if year is not None and (not isinstance(year, int) or not 1900 <= year <= 2100):
        warnings.append("INVALID_YEAR")

    penalty_by_warning = {
        "MISSING_TITLE": 0.55,
        "MISSING_STABLE_IDENTITY": 0.15,
        "MISSING_ABSTRACT": 0.15,
        "ARXIV_ID_CONFLICT": 0.65,
        "INVALID_YEAR": 0.1,
        "CROSS_SOURCE_TITLE_CONFLICT": 0.45,
    }
    penalty = min(sum(penalty_by_warning[item] for item in warnings), 1.0)
    return {
        "metadata_warnings": warnings,
        "metadata_quality_score": round(1.0 - penalty, 6),
    }


def _title_similarity(first: str, second: str) -> float:
    first_tokens = tokenize(first)
    second_tokens = tokenize(second)
    union = first_tokens | second_tokens
    if not union:
        return 1.0
    return len(first_tokens & second_tokens) / len(union)


def _deduplicate_candidates(
    document_groups: List[List[Dict[str, Any]]],
) -> list[Dict[str, Any]]:
    candidates: list[Dict[str, Any]] = []
    key_to_index: dict[str, int] = {}

    for group_index, documents in enumerate(document_groups):
        for source_rank, original in enumerate(documents, start=1):
            document = dict(original)
            source = str(document.get("source") or f"group_{group_index + 1}")
            keys = build_document_keys(document)
            duplicate_index = next(
                (key_to_index[key] for key in keys if key in key_to_index),
                None,
            )

            if duplicate_index is None:
                verification = verify_document_metadata(document)
                document.update(verification)
                document["sources"] = [source]
                document["source_ranks"] = {source: source_rank}
                candidates.append(document)
                index = len(candidates) - 1
                for key in keys:
                    key_to_index[key] = index
                continue

            existing = candidates[duplicate_index]
            if source not in existing["sources"]:
                existing["sources"].append(source)
            existing["source_ranks"][source] = min(
                source_rank,
                existing["source_ranks"].get(source, source_rank),
            )
            if _title_similarity(
                str(existing.get("title") or ""),
                str(document.get("title") or ""),
            ) < 0.35:
                warnings = existing.setdefault("metadata_warnings", [])
                if "CROSS_SOURCE_TITLE_CONFLICT" not in warnings:
                    warnings.append("CROSS_SOURCE_TITLE_CONFLICT")
                    existing["metadata_quality_score"] = round(
                        max(0.0, existing.get("metadata_quality_score", 1.0) - 0.45),
                        6,
                    )
            existing["cited_by_count"] = max(
                int(existing.get("cited_by_count") or 0),
                int(document.get("cited_by_count") or 0),
            )

    return candidates


def score_document(query: str, document: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate an auditable relevance score with no LLM call."""

    query_tokens = tokenize(query)
    title_tokens = tokenize(document.get("title"))
    content_tokens = tokenize(document.get("content") or document.get("summary"))
    denominator = max(len(query_tokens), 1)
    title_coverage = len(query_tokens & title_tokens) / denominator
    content_coverage = len(query_tokens & content_tokens) / denominator
    normalized_query = normalize_text(query)
    combined_text = normalize_text(
        f"{document.get('title', '')} {document.get('content', document.get('summary', ''))}"
    )
    phrase_match = float(bool(normalized_query and normalized_query in combined_text))
    ranks = list((document.get("source_ranks") or {}).values())
    reciprocal_rank = 1 / min(ranks) if ranks else 0.0
    source_diversity = min(max(len(document.get("sources") or []) - 1, 0), 1)
    citation_signal = min(math.log1p(int(document.get("cited_by_count") or 0)) / 10, 1.0)
    metadata_quality = float(document.get("metadata_quality_score", 1.0))

    signals = {
        "title_query_coverage": round(title_coverage, 6),
        "abstract_query_coverage": round(content_coverage, 6),
        "exact_query_phrase": phrase_match,
        "best_source_reciprocal_rank": round(reciprocal_rank, 6),
        "source_diversity": float(source_diversity),
        "citation_signal": round(citation_signal, 6),
        "metadata_quality": round(metadata_quality, 6),
    }
    score = (
        0.45 * title_coverage
        + 0.20 * content_coverage
        + 0.08 * phrase_match
        + 0.15 * reciprocal_rank
        + 0.04 * source_diversity
        + 0.03 * citation_signal
        + 0.05 * metadata_quality
    )
    return {"ranking_score": round(score, 6), "ranking_signals": signals}


def rerank_documents_with_stats(
    query: str,
    document_groups: List[List[Dict[str, Any]]],
    max_documents: int = 8,
) -> Dict[str, Any]:
    """Deduplicate all candidates, score them, then apply the Top-K limit."""

    raw_count = sum(len(group) for group in document_groups)
    candidates = _deduplicate_candidates(document_groups)
    for document in candidates:
        document.update(score_document(query, document))
    candidates.sort(
        key=lambda document: (
            -document["ranking_score"],
            min((document.get("source_ranks") or {"": 999}).values()),
        )
    )
    selected = candidates[:max_documents]
    return {
        "documents": selected,
        "raw_document_count": raw_count,
        "merged_document_count": len(selected),
        "deduplicated_count": max(raw_count - len(candidates), 0),
        "candidate_count_before_top_k": len(candidates),
        "metadata_warning_count": sum(
            bool(document.get("metadata_warnings")) for document in selected
        ),
        "ranking_strategy": "deterministic_cross_source_v1",
    }
