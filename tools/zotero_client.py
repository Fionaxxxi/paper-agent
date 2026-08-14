"""Zotero Web API v3 的最小只读客户端。"""

from __future__ import annotations

import re
from html import unescape
from typing import Any

import requests


class ZoteroReadOnlyClient:
    def __init__(
        self,
        *,
        base_url: str,
        library_type: str,
        library_id: str,
        api_key: str = "",
        timeout_seconds: float = 20.0,
        session: Any = requests,
    ) -> None:
        if library_type not in {"user", "group"}:
            raise ValueError("library_type 必须是 user 或 group")
        if not library_id.strip():
            raise ValueError("缺少 ZOTERO_LIBRARY_ID")
        if not library_id.strip().isdigit():
            raise ValueError("ZOTERO_LIBRARY_ID 必须是数字 ID")
        self.base_url = base_url.rstrip("/")
        self.prefix = f"{library_type}s/{library_id.strip()}"
        self.api_key = api_key.strip()
        self.timeout_seconds = timeout_seconds
        self.session = session

    @property
    def headers(self) -> dict[str, str]:
        headers = {"Zotero-API-Version": "3"}
        if self.api_key:
            headers["Zotero-API-Key"] = self.api_key
        return headers

    def search_items(
        self,
        *,
        query: str = "",
        tag: str = "",
        collection_key: str = "",
        limit: int = 5,
        include_notes: bool = True,
    ) -> dict[str, Any]:
        if limit < 1 or limit > 20:
            raise ValueError("limit 必须在 1 到 20 之间")
        if collection_key and not re.fullmatch(r"[A-Za-z0-9]+", collection_key):
            raise ValueError("collection_key 只能包含字母和数字")
        endpoint = (
            f"collections/{collection_key}/items/top"
            if collection_key
            else "items/top"
        )
        params: dict[str, Any] = {
            "format": "json",
            "limit": limit,
            "sort": "dateModified",
            "direction": "desc",
        }
        if query.strip():
            params.update({"q": query.strip(), "qmode": "everything"})
        if tag.strip():
            params["tag"] = tag.strip()
        response = self._get(endpoint, params=params)
        items = [self._normalize_item(row) for row in response.json()]
        if include_notes:
            for item in items:
                children = self._get(f"items/{item['item_key']}/children", params={"format": "json"}).json()
                item["notes"] = [
                    self._plain_text(child.get("data", {}).get("note", ""))[:2000]
                    for child in children
                    if child.get("data", {}).get("itemType") == "note"
                    and child.get("data", {}).get("note")
                ][:3]
                item["pdf_attachment_keys"] = [
                    child.get("key", "")
                    for child in children
                    if child.get("data", {}).get("itemType") == "attachment"
                    and child.get("data", {}).get("contentType") == "application/pdf"
                ]
        return {"items": items, "total_matches": self._total(response, len(items))}

    def _get(self, endpoint: str, *, params: dict[str, Any]):
        response = self.session.get(
            f"{self.base_url}/{self.prefix}/{endpoint}",
            headers=self.headers,
            params=params,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return response

    @staticmethod
    def _total(response: Any, fallback: int) -> int:
        try:
            return max(0, int(response.headers.get("Total-Results", fallback)))
        except (TypeError, ValueError):
            return fallback

    @staticmethod
    def _plain_text(value: str) -> str:
        return " ".join(unescape(re.sub(r"<[^>]+>", " ", value)).split())

    @staticmethod
    def _normalize_item(row: dict[str, Any]) -> dict[str, Any]:
        data = row.get("data", {})
        creators = []
        for creator in data.get("creators", []):
            name = creator.get("name") or " ".join(
                part for part in (creator.get("firstName", ""), creator.get("lastName", "")) if part
            )
            if name:
                creators.append(name)
        year_match = re.search(r"\b(?:19|20)\d{2}\b", str(data.get("date", "")))
        return {
            "item_key": row.get("key") or data.get("key", ""),
            "item_type": data.get("itemType", ""),
            "title": data.get("title", ""),
            "authors": creators,
            "year": int(year_match.group()) if year_match else None,
            "abstract": data.get("abstractNote", ""),
            "doi": data.get("DOI", ""),
            "url": data.get("url", ""),
            "tags": [tag.get("tag", "") for tag in data.get("tags", []) if tag.get("tag")],
            "collection_keys": list(data.get("collections", [])),
            "notes": [],
            "pdf_attachment_keys": [],
        }
