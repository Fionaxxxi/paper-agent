import time

import pytest
from pydantic import BaseModel, Field

import tools.arxiv_adapter as arxiv_adapter_module
from tools.crossref_adapter import CrossrefLookupTool
from tools.crossref_client import CrossrefClient
from tools.arxiv_adapter import ArxivLookupTool, ArxivSearchTool
from tools.contracts import (
    RetryPolicy,
    ToolErrorCode,
    ToolRiskLevel,
    ToolSpec,
    ToolRateLimitError,
)
from tools.executor import ToolExecutor
from tools.paper_models import PaperLookupInput, PaperSearchInput
from tools.registry import ToolRegistry
from tools.router import ToolRouter
from nodes.metrics import metrics_node


class DemoInput(BaseModel):
    value: int = Field(ge=1)


class DemoOutput(BaseModel):
    doubled: int


class FakeTool:
    def __init__(
        self,
        behavior,
        *,
        name="demo.tool",
        max_attempts=1,
        timeout=1.0,
        risk_level=ToolRiskLevel.READ_ONLY,
    ):
        self.behavior = behavior
        self.spec = ToolSpec(
            name=name,
            version="1.2.3",
            description="Deterministic test tool.",
            input_model=DemoInput,
            output_model=DemoOutput,
            provider="test",
            capabilities=("demo",),
            risk_level=risk_level,
            timeout_seconds=timeout,
            retry_policy=RetryPolicy(max_attempts=max_attempts),
        )

    def invoke(self, arguments):
        return self.behavior(arguments)


def test_registry_registers_discovers_and_filters_tools():
    registry = ToolRegistry()
    tool = FakeTool(lambda request: {"doubled": request.value * 2})

    registry.register(tool)

    assert registry.get("demo.tool") is tool
    assert registry.list_names() == ["demo.tool"]
    assert registry.list_by_capability("demo") == [tool]
    assert registry.list_by_capability("unknown") == []


def test_registry_rejects_duplicate_tool_names():
    registry = ToolRegistry()
    registry.register(FakeTool(lambda request: {"doubled": request.value * 2}))

    with pytest.raises(ValueError, match="already registered"):
        registry.register(FakeTool(lambda request: {"doubled": request.value * 3}))


def test_executor_returns_structured_error_for_unknown_tool():
    result = ToolExecutor(ToolRegistry()).execute("missing.tool", {"value": 1})

    assert result.success is False
    assert result.error_code == ToolErrorCode.TOOL_NOT_FOUND.value
    assert result.attempt_count == 0


def test_executor_rejects_invalid_input_without_invoking_tool():
    calls = []
    tool = FakeTool(lambda request: calls.append(request) or {"doubled": 2})
    registry = ToolRegistry()
    registry.register(tool)

    result = ToolExecutor(registry).execute("demo.tool", {"value": 0})

    assert result.success is False
    assert result.error_code == ToolErrorCode.INVALID_INPUT.value
    assert result.attempt_count == 0
    assert calls == []


def test_executor_blocks_non_read_only_tool_before_invocation():
    calls = []
    tool = FakeTool(
        lambda request: calls.append(request) or {"doubled": 2},
        risk_level=ToolRiskLevel.WRITE,
    )
    registry = ToolRegistry()
    registry.register(tool)

    result = ToolExecutor(registry).execute("demo.tool", {"value": 1})

    assert result.success is False
    assert result.error_code == ToolErrorCode.PERMISSION_DENIED.value
    assert result.attempt_count == 0
    assert calls == []


def test_executor_validates_output_and_records_execution_metadata():
    registry = ToolRegistry()
    registry.register(FakeTool(lambda request: {"doubled": request.value * 2}))

    result = ToolExecutor(registry).execute("demo.tool", {"value": 4})

    assert result.success is True
    assert result.data == {"doubled": 8}
    assert result.tool_version == "1.2.3"
    assert result.source == "test"
    assert result.attempt_count == 1
    assert result.latency_seconds >= 0
    assert result.metadata["risk_level"] == "read_only"
    assert result.metadata["capabilities"] == ["demo"]


def test_executor_retries_retryable_failure_then_returns_success():
    attempts = []

    def behavior(request):
        attempts.append(request.value)
        if len(attempts) == 1:
            raise ConnectionError("temporary failure")
        return {"doubled": request.value * 2}

    registry = ToolRegistry()
    registry.register(FakeTool(behavior, max_attempts=2))

    result = ToolExecutor(registry).execute("demo.tool", {"value": 3})

    assert result.success is True
    assert result.data == {"doubled": 6}
    assert result.attempt_count == 2
    assert attempts == [3, 3]


def test_executor_returns_structured_rate_limit_after_finite_retries():
    attempts = []

    def behavior(request):
        attempts.append(request.value)
        raise ToolRateLimitError("provider quota exhausted")

    registry = ToolRegistry()
    registry.register(FakeTool(behavior, max_attempts=2))

    result = ToolExecutor(registry).execute("demo.tool", {"value": 3})

    assert result.success is False
    assert result.error_code == ToolErrorCode.RATE_LIMITED.value
    assert result.attempt_count == 2
    assert attempts == [3, 3]


def test_executor_returns_timeout_after_bounded_wait():
    def behavior(request):
        time.sleep(0.05)
        return {"doubled": request.value * 2}

    registry = ToolRegistry()
    registry.register(FakeTool(behavior, timeout=0.005))

    result = ToolExecutor(registry).execute("demo.tool", {"value": 2})

    assert result.success is False
    assert result.error_code == ToolErrorCode.TIMEOUT.value
    assert result.attempt_count == 1


def test_executor_rejects_output_that_breaks_tool_contract():
    registry = ToolRegistry()
    registry.register(FakeTool(lambda request: {"unexpected": request.value}))

    result = ToolExecutor(registry).execute("demo.tool", {"value": 2})

    assert result.success is False
    assert result.error_code == ToolErrorCode.INVALID_OUTPUT.value
    assert result.attempt_count == 1


def test_router_resolves_registered_capability_and_source():
    router = ToolRouter()
    router.register_route("paper.search", "arxiv", "paper.search.arxiv")

    assert router.resolve("paper.search", "arxiv") == "paper.search.arxiv"

    with pytest.raises(KeyError, match="no tool route"):
        router.resolve("paper.search", "openalex")


def test_router_exposes_an_auditable_route_decision():
    router = ToolRouter()
    router.register_route(
        "paper.catalog.search", "mcp_catalog", "paper.catalog.search.mcp"
    )

    decision = router.select("paper.catalog.search", "mcp_catalog")

    assert decision.capability == "paper.catalog.search"
    assert decision.source == "mcp_catalog"
    assert decision.tool_name == "paper.catalog.search.mcp"


def test_arxiv_adapter_preserves_native_search_behavior(monkeypatch):
    calls = []

    def fake_search(query, max_results):
        calls.append((query, max_results))
        return [
            {
                "title": "Tool-Augmented Research Agents",
                "authors": ["Fiona"],
                "year": 2026,
                "summary": "A test paper.",
                "pdf_url": "https://example.com/paper.pdf",
                "entry_id": "1234.5678",
                "source": "arxiv",
            }
        ]

    monkeypatch.setattr(arxiv_adapter_module, "search_arxiv_papers", fake_search)

    output = ArxivSearchTool().invoke(
        PaperSearchInput(query="research agents", max_results=3)
    )

    assert calls == [("research agents", 3)]
    assert output["papers"][0]["entry_id"] == "1234.5678"


def test_arxiv_lookup_adapter_uses_native_identity_contract(monkeypatch):
    calls = []
    paper = {
        "title": "Canonical Paper",
        "authors": [],
        "year": 2024,
        "entry_id": "https://arxiv.org/abs/2401.01234",
        "source": "arxiv",
    }
    monkeypatch.setattr(
        arxiv_adapter_module,
        "lookup_arxiv_paper",
        lambda identity: calls.append(identity) or paper,
    )

    output = ArxivLookupTool().invoke(PaperLookupInput(identity="2401.01234"))

    assert calls == ["2401.01234"]
    assert output["paper"]["title"] == "Canonical Paper"


def test_crossref_client_normalizes_doi_metadata(monkeypatch):
    class Response:
        status_code = 200
        def raise_for_status(self): pass
        def json(self):
            return {"message": {"DOI": "10.1000/test", "title": ["Canonical DOI Paper"], "author": [{"given": "Ada", "family": "Lovelace"}], "published": {"date-parts": [[2024, 1, 2]]}, "URL": "https://doi.org/10.1000/test"}}

    calls = []
    monkeypatch.setattr("tools.crossref_client.requests.get", lambda url, **kwargs: calls.append((url, kwargs)) or Response())
    paper = CrossrefClient("https://api.crossref.org", "owner@example.com", 5).lookup_work("10.1000/test")

    assert paper["title"] == "Canonical DOI Paper"
    assert paper["authors"] == ["Ada Lovelace"]
    assert paper["source"] == "crossref"
    assert "10.1000%2Ftest" in calls[0][0]


def test_crossref_lookup_adapter_uses_shared_lookup_contract():
    class Client:
        def lookup_work(self, doi):
            return {"title": "DOI Paper", "doi": doi, "source": "crossref"}

    output = CrossrefLookupTool(Client()).invoke(PaperLookupInput(identity="10.1/demo"))

    assert output["paper"]["doi"] == "10.1/demo"


def test_semantic_scholar_client_normalizes_doi_metadata(monkeypatch):
    from tools.semantic_scholar_client import SemanticScholarClient

    class Response:
        status_code = 200
        def raise_for_status(self): pass
        def json(self):
            return {"title": "Canonical Paper", "authors": [{"name": "Ada Lovelace"}], "year": 2024, "externalIds": {"DOI": "10.1/demo"}, "url": "https://www.semanticscholar.org/paper/demo", "openAccessPdf": {"url": "https://example.com/demo.pdf"}}

    calls = []
    monkeypatch.setattr("tools.semantic_scholar_client.requests.get", lambda url, **kwargs: calls.append((url, kwargs)) or Response())
    paper = SemanticScholarClient("https://api.semanticscholar.org/graph/v1", "secret", 5).lookup_paper("10.1/demo")

    assert paper["source"] == "semantic_scholar"
    assert paper["authors"] == ["Ada Lovelace"]
    assert "DOI%3A10.1%2Fdemo" in calls[0][0]
    assert calls[0][1]["headers"]["x-api-key"] == "secret"


def test_semantic_scholar_adapter_uses_shared_lookup_contract():
    from tools.semantic_scholar_adapter import SemanticScholarLookupTool

    class Client:
        def lookup_paper(self, doi):
            return {"title": "DOI Paper", "doi": doi, "source": "semantic_scholar"}

    output = SemanticScholarLookupTool(Client()).invoke(PaperLookupInput(identity="10.1/demo"))

    assert output["paper"]["doi"] == "10.1/demo"


def test_semantic_scholar_client_maps_rate_limit_to_tool_error(monkeypatch):
    from tools.contracts import ToolRateLimitError
    from tools.semantic_scholar_client import SemanticScholarClient

    response = type("Response", (), {"status_code": 429})()
    monkeypatch.setattr("tools.semantic_scholar_client.requests.get", lambda *args, **kwargs: response)

    with pytest.raises(ToolRateLimitError):
        SemanticScholarClient("https://api.semanticscholar.org/graph/v1").lookup_paper("10.1/demo")


def test_metrics_reports_tool_execution_success_failure_and_latency():
    result = metrics_node(
        {
            "tools_used": ["paper.search.arxiv", "fallback_retriever"],
            "documents": [{"title": "Fallback"}],
            "paper_metadata": {
                "tool_executions": [
                    {
                        "tool_name": "paper.search.arxiv",
                        "tool_success": False,
                        "tool_error_code": ToolErrorCode.TIMEOUT.value,
                        "tool_latency_seconds": 1.25,
                    },
                    {
                        "tool_name": "paper.search.openalex",
                        "tool_success": True,
                        "tool_error_code": "",
                        "tool_latency_seconds": 0.75,
                    },
                ]
            },
            "node_timings": {},
            "llm_usage": [],
        }
    )

    metrics = result["paper_metadata"]["metrics"]
    assert metrics["tool_execution_count"] == 2
    assert metrics["tool_success_count"] == 1
    assert metrics["tool_failure_count"] == 1
    assert metrics["tool_latency_seconds"] == 2.0
    assert metrics["tool_executions"][0]["tool_error_code"] == "TIMEOUT"
