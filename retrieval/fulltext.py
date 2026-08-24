"""Bounded full-text enrichment for research retrieval results."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

from core.config import settings
from local_rag.bm25 import BM25Retriever
from local_rag.chunker import FixedWindowChunker
from local_rag.contracts import TextChunk
from local_rag.parser import PyPDFPageParser


DEEP_RESEARCH_SIGNALS = (
    "核心设计", "算法细节", "实验结果", "消融", "局限", "方法比较",
    "研究空白", "全文", "深入", "详细", "architecture", "experiment",
    "ablation", "limitation", "methodology",
)
TRUSTED_PDF_HOST_SUFFIXES = (
    "arxiv.org", "semanticscholar.org", "acm.org", "ieee.org",
    "springer.com", "springeropen.com", "openreview.net",
)


def needs_fulltext_research(state: dict[str, Any]) -> bool:
    """Only enrich tasks whose answer needs evidence beyond metadata/abstracts."""
    if not settings.FULLTEXT_RESEARCH_ENABLED:
        return False
    query = str(state.get("query") or "").casefold()
    task_type = str(state.get("task_type") or "").casefold()
    return (
        state.get("task_level") in {"L2", "L3"}
        or task_type in {"compare", "literature_review", "paper_critique"}
        or any(signal in query for signal in DEEP_RESEARCH_SIGNALS)
    )


def _safe_pdf_url(url: str) -> bool:
    parsed = urlparse(str(url or ""))
    host = (parsed.hostname or "").casefold().rstrip(".")
    return (
        parsed.scheme == "https"
        and bool(host)
        and any(host == suffix or host.endswith(f".{suffix}") for suffix in TRUSTED_PDF_HOST_SUFFIXES)
    )


def _document_identity(document: dict[str, Any]) -> str:
    raw = str(document.get("entry_id") or document.get("doi") or document.get("title") or "paper")
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", raw).strip("_")[:80] or "paper"


def _download_pdf(document: dict[str, Any]) -> tuple[Path | None, dict[str, Any]]:
    url = str(document.get("pdf_url") or "")
    if not _safe_pdf_url(url):
        return None, {"status": "skipped", "reason": "untrusted_or_missing_pdf_url"}

    cache_dir = Path(settings.FULLTEXT_CACHE_DIR)
    cache_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    path = cache_dir / f"{_document_identity(document)}_{digest}.pdf"
    if path.is_file() and path.stat().st_size > 0:
        return path, {"status": "cache_hit", "path": str(path)}

    limit = settings.FULLTEXT_MAX_PDF_MB * 1024 * 1024
    temporary = path.with_suffix(".part")
    try:
        with requests.get(
            url,
            timeout=settings.FULLTEXT_DOWNLOAD_TIMEOUT,
            stream=True,
            headers={"User-Agent": "PaperAgent/1.0 (research full-text reader)"},
        ) as response:
            response.raise_for_status()
            if not _safe_pdf_url(response.url):
                return None, {"status": "failed", "reason": "untrusted_pdf_redirect"}
            content_type = response.headers.get("content-type", "").casefold()
            if "pdf" not in content_type and not urlparse(response.url).path.casefold().endswith(".pdf"):
                return None, {"status": "failed", "reason": "response_is_not_pdf"}
            size = 0
            with temporary.open("wb") as output:
                for block in response.iter_content(64 * 1024):
                    if not block:
                        continue
                    size += len(block)
                    if size > limit:
                        raise ValueError("pdf_size_limit_exceeded")
                    output.write(block)
        temporary.replace(path)
        return path, {"status": "downloaded", "path": str(path), "bytes": size}
    except Exception as error:
        temporary.unlink(missing_ok=True)
        return None, {"status": "failed", "reason": f"{type(error).__name__}: {error}"}


def _rank_pdf_chunks(
    path: Path, document: dict[str, Any], query: str, limit: int
) -> list[dict[str, Any]]:
    document_id = _document_identity(document)
    pages = PyPDFPageParser().parse(path, document_id)
    chunks = FixedWindowChunker(chunk_size=1400, overlap=220).chunk(pages)
    if not chunks:
        return []
    ranked = BM25Retriever(chunks).search(query, limit)
    return [
        {
            **document,
            "content": chunk.text,
            "source": "online_pdf_fulltext",
            "document_id": document_id,
            "chunk_id": chunk.chunk_id,
            "page": chunk.page_start,
            "page_end": chunk.page_end,
            "retrieval_score": score,
            "content_scope": "fulltext_chunk",
            "fulltext_cached_path": str(path),
        }
        for chunk, score in ranked
    ]


def enrich_with_fulltext(
    documents: list[dict[str, Any]], state: dict[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Replace abstract-only evidence with query-relevant full-text chunks when possible."""
    if not needs_fulltext_research(state) or not documents:
        return documents, {"enabled": False, "status": "not_needed"}

    query = str(state.get("query") or state.get("rewritten_query") or "")
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for document in documents:
        identity = _document_identity(document).casefold()
        if identity not in seen:
            unique.append(document)
            seen.add(identity)

    fulltext: list[dict[str, Any]] = []
    statuses: list[dict[str, Any]] = []
    for document in unique[: settings.FULLTEXT_MAX_PAPERS]:
        path, status = _download_pdf(document)
        status = {**status, "title": document.get("title", "")}
        if path is not None:
            try:
                chunks = _rank_pdf_chunks(
                    path, document, query, settings.FULLTEXT_CHUNKS_PER_PAPER
                )
                fulltext.extend(chunks)
                status["chunk_count"] = len(chunks)
            except Exception as error:
                status = {**status, "status": "failed", "reason": f"parse_error:{type(error).__name__}"}
        statuses.append(status)

    if not fulltext:
        return documents, {"enabled": True, "status": "unavailable", "papers": statuses, "chunk_count": 0}

    return [*fulltext, *documents], {
        "enabled": True,
        "status": "enriched",
        "papers": statuses,
        "chunk_count": len(fulltext),
        "paper_count": sum(1 for item in statuses if item.get("chunk_count", 0) > 0),
    }
