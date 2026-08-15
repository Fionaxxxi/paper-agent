"""GitHub REST API 的固定端点只读客户端。"""

from __future__ import annotations

import base64
import re
from typing import Any
from urllib.parse import quote

import requests


_REPOSITORY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_DEPENDENCY_FILES = {
    "requirements.txt", "pyproject.toml", "setup.py", "setup.cfg", "environment.yml",
    "environment.yaml", "package.json", "pnpm-lock.yaml", "yarn.lock", "cargo.toml",
    "go.mod", "pom.xml", "build.gradle", "build.gradle.kts",
}


class GitHubReadOnlyClient:
    def __init__(self, *, base_url: str = "https://api.github.com", token: str = "", timeout_seconds: float = 20.0, session: Any = requests) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token.strip()
        self.timeout_seconds = timeout_seconds
        self.session = session

    @property
    def headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "PaperAgent/1.0",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def search_repositories(self, *, query: str, limit: int = 5) -> dict[str, Any]:
        query = query.strip()
        if not query:
            raise ValueError("query 不能为空")
        if limit < 1 or limit > 10:
            raise ValueError("limit 必须在 1 到 10 之间")
        response = self._get("search/repositories", params={"q": query, "per_page": limit, "sort": "stars", "order": "desc"})
        payload = response.json()
        repositories = [self._normalize_repository(row) for row in payload.get("items", [])]
        return {"repositories": repositories, "total_matches": max(0, int(payload.get("total_count", len(repositories))))}

    def inspect_repository(self, *, repository: str, tree_limit: int = 100, activity_limit: int = 3) -> dict[str, Any]:
        repository = self._validate_repository(repository)
        if tree_limit < 1 or tree_limit > 300:
            raise ValueError("tree_limit 必须在 1 到 300 之间")
        if activity_limit < 1 or activity_limit > 5:
            raise ValueError("activity_limit 必须在 1 到 5 之间")

        repo = self._get(f"repos/{repository}", params={}).json()
        default_branch = str(repo.get("default_branch") or "main")
        readme = self._optional_json(f"repos/{repository}/readme")
        tree = self._optional_json(f"repos/{repository}/git/trees/{quote(default_branch, safe='')}", params={"recursive": "1"})
        all_paths = [str(row.get("path")) for row in tree.get("tree", []) if row.get("type") == "blob" and row.get("path")]
        paths = all_paths[:tree_limit]
        dependency_paths = [path for path in all_paths if path.rsplit("/", 1)[-1].lower() in _DEPENDENCY_FILES][:5]
        dependencies = []
        for path in dependency_paths:
            content = self._optional_json(f"repos/{repository}/contents/{quote(path, safe='/')}")
            dependencies.append({"path": path, "content": self._decode_content(content)[:4000]})

        issues_payload = self._optional_json(f"repos/{repository}/issues", params={"state": "open", "sort": "updated", "direction": "desc", "per_page": 100}, default=[])
        releases_payload = self._optional_json(f"repos/{repository}/releases", params={"per_page": activity_limit}, default=[])
        commits_payload = self._optional_json(f"repos/{repository}/commits", params={"per_page": activity_limit}, default=[])
        return {
            "repository": self._normalize_repository(repo),
            "readme": self._decode_content(readme)[:12000],
            "tree_paths": paths,
            "dependencies": dependencies,
            "open_issues": [{"number": row.get("number"), "title": row.get("title", ""), "url": row.get("html_url", ""), "updated_at": row.get("updated_at", "")} for row in issues_payload if "pull_request" not in row][:activity_limit],
            "releases": [{"tag": row.get("tag_name", ""), "name": row.get("name", ""), "url": row.get("html_url", ""), "published_at": row.get("published_at", "")} for row in releases_payload[:activity_limit]],
            "recent_commits": [{"sha": str(row.get("sha", ""))[:12], "message": row.get("commit", {}).get("message", "").splitlines()[0], "url": row.get("html_url", ""), "date": row.get("commit", {}).get("author", {}).get("date", "")} for row in commits_payload[:activity_limit]],
        }

    def _get(self, endpoint: str, *, params: dict[str, Any]):
        response = self.session.get(f"{self.base_url}/{endpoint}", headers=self.headers, params=params, timeout=self.timeout_seconds)
        response.raise_for_status()
        return response

    def _optional_json(self, endpoint: str, *, params: dict[str, Any] | None = None, default: Any = None) -> Any:
        response = self.session.get(f"{self.base_url}/{endpoint}", headers=self.headers, params=params or {}, timeout=self.timeout_seconds)
        if getattr(response, "status_code", 200) == 404:
            return {} if default is None else default
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _validate_repository(repository: str) -> str:
        repository = repository.strip()
        if not _REPOSITORY_PATTERN.fullmatch(repository):
            raise ValueError("repository 必须是 owner/repo 格式")
        if any(part in {".", ".."} for part in repository.split("/")):
            raise ValueError("repository 不能包含相对路径片段")
        return repository

    @staticmethod
    def _decode_content(payload: dict[str, Any]) -> str:
        content = str(payload.get("content") or "").replace("\n", "")
        if payload.get("encoding") != "base64" or not content:
            return ""
        try:
            return base64.b64decode(content).decode("utf-8", errors="replace")
        except (ValueError, TypeError):
            return ""

    @staticmethod
    def _normalize_repository(row: dict[str, Any]) -> dict[str, Any]:
        owner = row.get("owner") or {}
        return {"full_name": row.get("full_name", ""), "owner": owner.get("login", ""), "name": row.get("name", ""), "description": row.get("description") or "", "url": row.get("html_url", ""), "stars": int(row.get("stargazers_count") or 0), "language": row.get("language") or "", "topics": list(row.get("topics") or []), "default_branch": row.get("default_branch") or "", "updated_at": row.get("updated_at") or ""}
