"""Small HTTP client for the OpenAlex Works API."""

from __future__ import annotations

from typing import Any

import requests

from tools.contracts import ToolRateLimitError


OPENALEX_WORK_FIELDS = (
    "id",
    "doi",
    "title",
    "display_name",
    "publication_year",
    "authorships",
    "abstract_inverted_index",
    "primary_location",
    "best_oa_location",
    "cited_by_count",
)


def reconstruct_abstract(inverted_index: dict[str, list[int]] | None) -> str:
    """Rebuild plain abstract text from OpenAlex's inverted index."""

    if not inverted_index:
        return ""

    positioned_words = [
        (position, word)
        for word, positions in inverted_index.items()
        for position in positions
    ]
    positioned_words.sort(key=lambda item: item[0])
    return " ".join(word for _, word in positioned_words)


def normalize_openalex_work(work: dict[str, Any]) -> dict[str, Any]:
    """Map an OpenAlex Work object to PaperAgent's stable paper contract."""

    authors = []
    for authorship in work.get("authorships") or []:
        author = authorship.get("author") or {}
        name = author.get("display_name")
        if name:
            authors.append(name)

    primary_location = work.get("primary_location") or {}
    best_oa_location = work.get("best_oa_location") or {}
    pdf_url = best_oa_location.get("pdf_url") or primary_location.get("pdf_url") or ""
    landing_page_url = (
        best_oa_location.get("landing_page_url")
        or primary_location.get("landing_page_url")
        or work.get("doi")
        or work.get("id")
        or ""
    )

    return {
        "title": work.get("title") or work.get("display_name") or "",
        "authors": authors,
        "year": work.get("publication_year"),
        "summary": reconstruct_abstract(work.get("abstract_inverted_index")),
        "pdf_url": pdf_url,
        "entry_id": work.get("id") or "",
        "doi": work.get("doi") or "",
        "cited_by_count": max(int(work.get("cited_by_count") or 0), 0),
        "landing_page_url": landing_page_url,
        "source": "openalex",
    }


class OpenAlexClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str = "",
        mailto: str = "",
        timeout_seconds: float = 30.0,
        session: requests.Session | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key.strip()
        self.mailto = mailto.strip()
        self.timeout_seconds = timeout_seconds
        self.session = session or requests.Session()

    def search_works(self, query: str, max_results: int) -> list[dict[str, Any]]:
        params = {
            "search": query,
            "per-page": max_results,
            "select": ",".join(OPENALEX_WORK_FIELDS),
        }
        if self.api_key:
            params["api_key"] = self.api_key
        if self.mailto:
            params["mailto"] = self.mailto

        response = self.session.get(
            f"{self.base_url}/works",
            params=params,
            headers={"User-Agent": "PaperAgent/1.0"},
            timeout=self.timeout_seconds,
        )
        if response.status_code == 429:
            raise ToolRateLimitError(
                "OpenAlex rate limit exceeded; configure OPENALEX_API_KEY or retry later"
            )
        response.raise_for_status()
        payload = response.json()
        results = payload.get("results", [])
        if not isinstance(results, list):
            raise ValueError("OpenAlex response field 'results' must be a list")

        papers = [normalize_openalex_work(work) for work in results]
        return [paper for paper in papers if paper["title"]][:max_results]
