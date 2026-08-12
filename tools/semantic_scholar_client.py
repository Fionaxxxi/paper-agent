"""Semantic Scholar DOI lookup client behind the shared authority contract."""

from __future__ import annotations

from urllib.parse import quote

import requests

from tools.contracts import ToolRateLimitError


class SemanticScholarClient:
    def __init__(self, base_url: str, api_key: str = "", timeout_seconds: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key.strip()
        self.timeout_seconds = timeout_seconds

    def lookup_paper(self, doi: str) -> dict | None:
        headers = {"User-Agent": "PaperAgent/0.1"}
        if self.api_key:
            headers["x-api-key"] = self.api_key
        response = requests.get(
            f"{self.base_url}/paper/{quote(f'DOI:{doi}', safe='')}",
            params={"fields": "title,authors,year,abstract,url,externalIds,openAccessPdf"},
            headers=headers,
            timeout=self.timeout_seconds,
        )
        if response.status_code == 404:
            return None
        if response.status_code == 429:
            raise ToolRateLimitError(
                "Semantic Scholar rate limit exceeded; configure SEMANTIC_SCHOLAR_API_KEY or retry later"
            )
        response.raise_for_status()
        message = response.json()
        external_ids = message.get("externalIds") or {}
        open_access_pdf = message.get("openAccessPdf") or {}
        return {
            "title": message.get("title") or "",
            "authors": [
                author.get("name", "")
                for author in message.get("authors") or []
                if author.get("name")
            ],
            "year": message.get("year"),
            "summary": message.get("abstract") or "",
            "pdf_url": open_access_pdf.get("url") or "",
            "entry_id": message.get("url") or "",
            "doi": external_ids.get("DOI") or doi,
            "landing_page_url": message.get("url") or "",
            "source": "semantic_scholar",
        }
