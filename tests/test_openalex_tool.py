import pytest

from retrieval.cache import build_cache_key
from tools.openalex_adapter import OpenAlexSearchTool
from tools.openalex_client import OpenAlexClient, normalize_openalex_work, reconstruct_abstract
from tools.paper_models import PaperSearchInput
from tools.runtime import paper_tool_router, tool_registry
from tools.contracts import ToolRateLimitError


class FakeResponse:
    def __init__(self, payload, error=None, status_code=200):
        self.payload = payload
        self.error = error
        self.status_code = status_code

    def raise_for_status(self):
        if self.error:
            raise self.error

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.response


def sample_work():
    return {
        "id": "https://openalex.org/W123",
        "doi": "https://doi.org/10.1000/test",
        "title": "Open Scholarly Graphs",
        "publication_year": 2025,
        "authorships": [
            {"author": {"display_name": "Fiona"}},
            {"author": {"display_name": "Researcher Two"}},
        ],
        "abstract_inverted_index": {
            "Open": [0],
            "graphs": [2],
            "scholarly": [1],
        },
        "primary_location": {
            "landing_page_url": "https://example.org/work",
            "pdf_url": None,
        },
        "best_oa_location": {
            "landing_page_url": "https://example.org/oa",
            "pdf_url": "https://example.org/work.pdf",
        },
        "cited_by_count": 42,
    }


def test_reconstruct_abstract_orders_openalex_inverted_positions():
    assert reconstruct_abstract(sample_work()["abstract_inverted_index"]) == (
        "Open scholarly graphs"
    )
    assert reconstruct_abstract(None) == ""


def test_normalize_openalex_work_maps_stable_paper_fields():
    paper = normalize_openalex_work(sample_work())

    assert paper["title"] == "Open Scholarly Graphs"
    assert paper["authors"] == ["Fiona", "Researcher Two"]
    assert paper["summary"] == "Open scholarly graphs"
    assert paper["pdf_url"] == "https://example.org/work.pdf"
    assert paper["doi"] == "https://doi.org/10.1000/test"
    assert paper["cited_by_count"] == 42
    assert paper["source"] == "openalex"


def test_openalex_client_sends_search_limits_identity_and_optional_key():
    session = FakeSession(FakeResponse({"results": [sample_work()]}))
    client = OpenAlexClient(
        base_url="https://api.openalex.org/",
        api_key="test-key",
        mailto="owner@example.com",
        timeout_seconds=7.5,
        session=session,
    )

    papers = client.search_works("graph research", 3)

    url, request = session.calls[0]
    assert url == "https://api.openalex.org/works"
    assert request["params"]["search"] == "graph research"
    assert request["params"]["per-page"] == 3
    assert request["params"]["api_key"] == "test-key"
    assert request["params"]["mailto"] == "owner@example.com"
    assert request["headers"]["User-Agent"] == "PaperAgent/1.0"
    assert request["timeout"] == 7.5
    assert papers[0]["entry_id"] == "https://openalex.org/W123"


def test_openalex_client_maps_rate_limit_for_executor_recovery():
    client = OpenAlexClient(
        base_url="https://api.openalex.org",
        session=FakeSession(FakeResponse({}, status_code=429)),
    )

    with pytest.raises(ToolRateLimitError, match="rate limit"):
        client.search_works("rate limit", 2)


def test_openalex_adapter_delegates_to_injected_client():
    calls = []

    class FakeClient:
        def search_works(self, query, max_results):
            calls.append((query, max_results))
            return [normalize_openalex_work(sample_work())]

    output = OpenAlexSearchTool(client=FakeClient()).invoke(
        PaperSearchInput(query="open graphs", max_results=4)
    )

    assert calls == [("open graphs", 4)]
    assert output["papers"][0]["source"] == "openalex"


def test_default_runtime_registers_and_routes_openalex_tool():
    assert tool_registry.get("paper.search.openalex") is not None
    assert paper_tool_router.resolve("paper.search", "openalex") == (
        "paper.search.openalex"
    )


def test_cache_keys_are_isolated_by_paper_source():
    arxiv_key = build_cache_key("Graph RAG", source="arxiv")
    openalex_key = build_cache_key("Graph RAG", source="openalex")

    assert arxiv_key != openalex_key
    assert arxiv_key == build_cache_key(" graph rag ", source="ARXIV")
