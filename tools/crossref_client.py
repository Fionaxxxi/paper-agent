"""Minimal Crossref DOI lookup client behind the authority tool contract."""

from __future__ import annotations

from urllib.parse import quote

import requests


class CrossrefClient:
    def __init__(self, base_url: str, mailto: str = "", timeout_seconds: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.mailto = mailto.strip()
        self.timeout_seconds = timeout_seconds

    def lookup_work(self, doi: str) -> dict | None:
        headers = {"User-Agent": "PaperAgent/0.1"}
        if self.mailto:
            headers["User-Agent"] += f" (mailto:{self.mailto})"
        response = requests.get(
            f"{self.base_url}/works/{quote(doi, safe='')}",
            headers=headers,
            timeout=self.timeout_seconds,
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        message = response.json().get("message") or {}
        titles = message.get("title") or []
        authors = [
            " ".join(part for part in (author.get("given", ""), author.get("family", "")) if part)
            for author in message.get("author") or []
        ]
        date_parts = (message.get("published") or message.get("issued") or {}).get("date-parts") or []
        year = date_parts[0][0] if date_parts and date_parts[0] else None
        return {
            "title": titles[0] if titles else "",
            "authors": [author for author in authors if author],
            "year": year,
            "summary": message.get("abstract") or "",
            "entry_id": message.get("URL") or "",
            "doi": message.get("DOI") or doi,
            "landing_page_url": message.get("URL") or "",
            "source": "crossref",
        }
