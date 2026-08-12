import time

import nodes.retrieve as retrieve_module
from eval_harness.parallel_retrieval_eval import build_report


def _source_result(source):
    return {"papers": [{"title": f"{source} paper", "source": source, "entry_id": source}], "provider": source, "retrieval_source": source, "cache_hit": False, "tools_used": [source], "tool_execution": {}}


def test_parallel_retrieval_preserves_configured_source_order(monkeypatch):
    monkeypatch.setattr(retrieve_module.settings, "RETRIEVAL_MODE", "multi")
    monkeypatch.setattr(retrieve_module.settings, "MULTI_SOURCE_PROVIDERS", "arxiv,openalex")
    monkeypatch.setattr(retrieve_module.settings, "MULTI_SOURCE_PARALLEL_ENABLED", True)
    monkeypatch.setattr(retrieve_module, "retrieve_from_source", lambda query, state, source: (time.sleep(0.03 if source == "arxiv" else 0.001) or _source_result(source)))

    result = retrieve_module.retrieve_by_query("query", {})

    assert [row["provider"] for row in result["source_statuses"]] == ["arxiv", "openalex"]
    assert [row["title"] for row in result["documents"]] == ["arxiv paper", "openalex paper"]


def test_parallel_retrieval_keeps_partial_success(monkeypatch):
    monkeypatch.setattr(retrieve_module.settings, "RETRIEVAL_MODE", "multi")
    monkeypatch.setattr(retrieve_module.settings, "MULTI_SOURCE_PROVIDERS", "arxiv,openalex")
    monkeypatch.setattr(retrieve_module.settings, "MULTI_SOURCE_PARALLEL_ENABLED", True)
    monkeypatch.setattr(retrieve_module, "retrieve_from_source", lambda query, state, source: _source_result(source) if source == "openalex" else {**_source_result(source), "papers": []})

    result = retrieve_module.retrieve_by_query("query", {})

    assert [row["title"] for row in result["documents"]] == ["openalex paper"]
    assert result["retrieval_source"] == "multi_source"


def test_single_source_does_not_create_parallel_pool(monkeypatch):
    monkeypatch.setattr(retrieve_module.settings, "RETRIEVAL_MODE", "arxiv")
    monkeypatch.setattr(retrieve_module.settings, "MULTI_SOURCE_PARALLEL_ENABLED", True)
    monkeypatch.setattr(retrieve_module, "retrieve_from_source", lambda query, state, source: _source_result(source))
    monkeypatch.setattr(retrieve_module, "ThreadPoolExecutor", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("pool should not be used")))

    result = retrieve_module.retrieve_by_query("query", {})

    assert result["documents"][0]["title"] == "arxiv paper"


def test_parallel_benchmark_reports_repeatable_speedup_and_equivalence():
    report = build_report(repetitions=3)

    assert report["repetitions"] == 3
    assert report["speedup"] > 1.5
    assert report["latency_reduction_pct"] > 30
    assert report["result_equality_rate"] == 1.0
