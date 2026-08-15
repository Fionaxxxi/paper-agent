import base64

import pytest

from tools.github_client import GitHubReadOnlyClient
from tools.mcp_github import build_github_inspect_mcp_tool
from tools.runtime import paper_tool_router, tool_registry


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.pop(0)


def _repo():
    return {
        "full_name": "microsoft/graphrag", "name": "graphrag",
        "owner": {"login": "microsoft"}, "description": "GraphRAG",
        "html_url": "https://github.com/microsoft/graphrag", "stargazers_count": 999,
        "language": "Python", "topics": ["rag"], "default_branch": "main",
        "updated_at": "2026-01-01T00:00:00Z",
    }


def _encoded(text):
    return {"encoding": "base64", "content": base64.b64encode(text.encode()).decode()}


def test_github_search_uses_versioned_get_and_keeps_token_out_of_url():
    session = FakeSession([FakeResponse({"total_count": 1, "items": [_repo()]})])
    client = GitHubReadOnlyClient(token="secret-token", session=session)

    result = client.search_repositories(query="graph rag", limit=1)

    assert result["repositories"][0]["full_name"] == "microsoft/graphrag"
    url, kwargs = session.calls[0]
    assert "secret-token" not in url
    assert kwargs["headers"]["Authorization"] == "Bearer secret-token"
    assert kwargs["headers"]["X-GitHub-Api-Version"] == "2022-11-28"
    assert kwargs["params"]["q"] == "graph rag"


def test_github_inspect_normalizes_implementation_evidence():
    session = FakeSession([
        FakeResponse(_repo()),
        FakeResponse(_encoded("# GraphRAG\nImplementation")),
        FakeResponse({"tree": [{"type": "blob", "path": "pyproject.toml"}, {"type": "blob", "path": "graphrag/main.py"}]}),
        FakeResponse(_encoded("[project]\nname='graphrag'")),
        FakeResponse([{"number": 9, "title": "PR", "pull_request": {}}, {"number": 7, "title": "Open issue", "html_url": "https://example/7", "updated_at": "now"}]),
        FakeResponse([{"tag_name": "v1.0", "name": "Stable", "html_url": "https://example/release", "published_at": "now"}]),
        FakeResponse([{"sha": "1234567890abcdef", "html_url": "https://example/commit", "commit": {"message": "fix: improve indexing\nbody", "author": {"date": "now"}}}]),
    ])
    client = GitHubReadOnlyClient(session=session)

    result = client.inspect_repository(repository="microsoft/graphrag", activity_limit=2)

    assert result["readme"].startswith("# GraphRAG")
    assert result["dependencies"] == [{"path": "pyproject.toml", "content": "[project]\nname='graphrag'"}]
    assert result["open_issues"][0]["number"] == 7
    assert result["recent_commits"][0]["sha"] == "1234567890ab"
    assert result["recent_commits"][0]["message"] == "fix: improve indexing"


def test_github_tools_are_registered_read_only_and_explicitly_routed():
    search = tool_registry.get("code.repository.search.github.mcp")
    inspect = tool_registry.get("code.repository.inspect.github.mcp")

    assert search.spec.risk_level.value == "read_only"
    assert inspect.spec.risk_level.value == "read_only"
    assert paper_tool_router.resolve("repository.search", "github") == search.spec.name
    assert paper_tool_router.resolve("repository.inspect", "github") == inspect.spec.name
    assert inspect.audit_metadata["mcp_server"] == "paperagent-github"


def test_github_repository_schema_rejects_path_or_url_injection():
    model = build_github_inspect_mcp_tool().spec.input_model
    for invalid in ("../secret", "https://github.com/microsoft/graphrag", "owner/repo/issues"):
        with pytest.raises(ValueError):
            model.model_validate({"repository": invalid})
