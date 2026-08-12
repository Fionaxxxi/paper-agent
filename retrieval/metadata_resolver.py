"""Deterministic metadata provenance checks for multi-source paper records."""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable

from retrieval.result_merger import normalize_text


ARXIV_ID_PATTERN = re.compile(r"(?<!\d)(\d{4}\.\d{4,5})(?:v\d+)?(?!\d)", re.IGNORECASE)
WORD_PATTERN = re.compile(r"[a-z0-9]+|[\u4e00-\u9fff]", re.IGNORECASE)
QUERY_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "in", "is", "of", "on", "or", "that", "the", "to", "using", "with",
    "what", "why", "how", "paper", "papers", "research", "study",
}


def normalize_doi(value: Any) -> str:
    """Normalize DOI URLs and prefixes to one stable identity value."""

    normalized = normalize_text(value)
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        normalized = normalized.removeprefix(prefix)
    return normalized


def extract_arxiv_ids(document: Dict[str, Any]) -> set[str]:
    """Extract arXiv identities from every field that may carry one."""

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


def _tokens(value: Any) -> set[str]:
    return {
        token.casefold()
        for token in WORD_PATTERN.findall(str(value or ""))
        if token.casefold() not in QUERY_STOPWORDS
    }


def title_similarity(first: Any, second: Any) -> float:
    first_tokens = _tokens(first)
    second_tokens = _tokens(second)
    union = first_tokens | second_tokens
    if not union:
        return 1.0
    return len(first_tokens & second_tokens) / len(union)


def title_query_support(query: str, title: str) -> float:
    """Measure whether a returned title is plausibly about the submitted query."""

    query_tokens = _tokens(query)
    title_tokens = _tokens(title)
    denominator = min(len(query_tokens), len(title_tokens))
    if denominator == 0:
        return 0.0
    return len(query_tokens & title_tokens) / denominator


def metadata_evidence(document: Dict[str, Any]) -> Dict[str, Any]:
    """Keep only auditable metadata fields from one provider response."""

    return {
        field: document.get(field)
        for field in (
            "source", "title", "authors", "year", "content", "summary", "doi",
            "entry_id", "pdf_url", "landing_page_url", "cited_by_count",
        )
    }


def attach_authoritative_evidence(
    document: Dict[str, Any],
    authority_by_identity: Dict[str, Dict[str, Any]] | None,
) -> Dict[str, Any]:
    """Attach separately acquired canonical evidence without mutating the input."""

    enriched = dict(document)
    if not authority_by_identity:
        return enriched
    evidences = list(enriched.get("metadata_evidence") or [metadata_evidence(enriched)])
    for arxiv_id in extract_arxiv_ids(enriched):
        authority = authority_by_identity.get(f"arxiv:{arxiv_id}")
        if authority is not None:
            if authority.get("canonical_lookup_status") == "NOT_FOUND":
                enriched["canonical_authority_not_found"] = True
            else:
                evidences.append(metadata_evidence(authority))
    doi = normalize_doi(enriched.get("doi"))
    if doi and not doi.startswith("10.48550/arxiv."):
        authority = authority_by_identity.get(f"doi:{doi}")
        if authority is not None:
            if authority.get("canonical_lookup_status") == "NOT_FOUND":
                enriched["doi_authority_not_found"] = True
            else:
                evidences.append(metadata_evidence(authority))
    enriched["metadata_evidence"] = evidences
    return enriched


def _native_arxiv_evidence(
    evidences: Iterable[Dict[str, Any]],
    arxiv_id: str,
) -> Dict[str, Any] | None:
    for evidence in evidences:
        if normalize_text(evidence.get("source")) != "arxiv":
            continue
        if arxiv_id in extract_arxiv_ids(evidence):
            return evidence
    return None


def _canonical_doi_evidence(
    evidences: Iterable[Dict[str, Any]],
    doi: str,
) -> Dict[str, Any] | None:
    for evidence in evidences:
        if normalize_text(evidence.get("source")) != "crossref":
            continue
        if normalize_doi(evidence.get("doi")) == doi:
            return evidence
    return None


def _copy_authoritative_fields(
    document: Dict[str, Any],
    authoritative: Dict[str, Any],
    authority_name: str = "ARXIV",
) -> list[str]:
    repairs: list[str] = []
    for field in ("title", "authors", "year", "pdf_url", "doi"):
        canonical_value = authoritative.get(field)
        if not canonical_value:
            continue
        current_value = document.get(field)
        conflicts = field == "title" and title_similarity(current_value, canonical_value) < 0.35
        if not current_value or conflicts:
            if current_value != canonical_value:
                document[field] = canonical_value
                repairs.append(f"REPAIRED_{field.upper()}_FROM_{authority_name}")
    abstract_field = "content" if "content" in document else "summary"
    canonical_abstract = authoritative.get(abstract_field)
    if not document.get(abstract_field) and canonical_abstract:
        document[abstract_field] = canonical_abstract
        repairs.append(f"REPAIRED_ABSTRACT_FROM_{authority_name}")
    return repairs


def resolve_document_metadata(query: str, document: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve provenance, repair from native authority, or quarantine unsafe claims.

    arXiv is authoritative only for an arXiv identity carried by a native arXiv
    response. A secondary provider's arXiv DOI remains an unverified claim until
    another source confirms it. If that claim also contradicts the query title,
    the record is isolated from ranking instead of being silently trusted.
    """

    resolved = dict(document)
    evidences = list(resolved.get("metadata_evidence") or [metadata_evidence(resolved)])
    warnings = list(resolved.get("metadata_warnings") or [])
    repairs: list[str] = []
    all_arxiv_ids = set().union(*(extract_arxiv_ids(item) for item in evidences))
    canonical_identity = ""
    status = "UNVERIFIED"
    action = "KEEP"
    quarantined = False

    if len(all_arxiv_ids) > 1:
        warnings.append("CONFLICTING_ARXIV_IDENTITIES")
        status = "CONFLICT"
        action = "QUARANTINE"
        quarantined = True
    elif all_arxiv_ids:
        arxiv_id = next(iter(all_arxiv_ids))
        canonical_identity = f"arxiv:{arxiv_id}"
        authoritative = _native_arxiv_evidence(evidences, arxiv_id)
        if authoritative is not None:
            repairs = _copy_authoritative_fields(resolved, authoritative)
            conflicts = [
                item for item in evidences
                if item is not authoritative
                and item.get("title")
                and title_similarity(authoritative.get("title"), item.get("title")) < 0.35
            ]
            if conflicts:
                warnings.append("SECONDARY_TITLE_CONFLICT")
            status = "AUTHORITATIVE_REPAIRED" if repairs else "AUTHORITATIVE_VERIFIED"
            action = "REPAIR" if repairs else "KEEP"
        else:
            if resolved.get("canonical_authority_not_found"):
                warnings.append("ARXIV_ID_NOT_FOUND_IN_NATIVE_SOURCE")
                status = "AUTHORITATIVE_NOT_FOUND"
                action = "QUARANTINE"
                quarantined = True
                support = 0.0
            else:
                support = title_query_support(query, str(resolved.get("title") or ""))
            if not quarantined and support < 0.2:
                warnings.append("UNVERIFIED_ARXIV_ID_TITLE_MISMATCH")
                status = "UNVERIFIED_CONFLICT"
                action = "QUARANTINE"
                quarantined = True
            elif not quarantined:
                warnings.append("UNVERIFIED_ARXIV_IDENTITY")
                status = "SECONDARY_ACCEPTED"
    else:
        doi = normalize_doi(resolved.get("doi"))
        if doi:
            canonical_identity = f"doi:{doi}"
            authoritative = _canonical_doi_evidence(evidences, doi)
            if authoritative is not None:
                repairs = _copy_authoritative_fields(
                    resolved, authoritative, "CROSSREF"
                )
                conflicts = [
                    item for item in evidences
                    if item is not authoritative
                    and item.get("title")
                    and title_similarity(authoritative.get("title"), item.get("title")) < 0.35
                ]
                if conflicts:
                    warnings.append("SECONDARY_TITLE_CONFLICT")
                status = "DOI_AUTHORITATIVE_REPAIRED" if repairs else "DOI_AUTHORITATIVE_VERIFIED"
                action = "REPAIR" if repairs else "KEEP"
            elif resolved.get("doi_authority_not_found"):
                warnings.append("DOI_AUTHORITY_NOT_FOUND")
                status = "DOI_AUTHORITY_NOT_FOUND"
            else:
                status = "CONSENSUS_VERIFIED" if len(resolved.get("sources") or []) > 1 else "SOURCE_ACCEPTED"
        elif resolved.get("entry_id"):
            canonical_identity = f"entry_id:{normalize_text(resolved['entry_id'])}"
            status = "CONSENSUS_VERIFIED" if len(resolved.get("sources") or []) > 1 else "SOURCE_ACCEPTED"
        else:
            status = "CONSENSUS_VERIFIED" if len(resolved.get("sources") or []) > 1 else "SOURCE_ACCEPTED"

    resolved["metadata_warnings"] = list(dict.fromkeys(warnings))
    resolved["metadata_repairs"] = repairs
    resolved["metadata_resolution_status"] = status
    resolved["metadata_resolution_action"] = action
    resolved["canonical_identity"] = canonical_identity
    resolved["metadata_quarantined"] = quarantined
    return resolved
