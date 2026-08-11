import json

import pytest
from pydantic import ValidationError

from eval_harness.retrieval_eval_models import (
    RetrievalEvalDataset,
    load_retrieval_dataset,
)
from eval_harness.retrieval_metrics import (
    calculate_case_metrics,
    duplicate_rate,
    extract_arxiv_id,
    normalize_doi,
    normalize_title,
    paper_identity_keys,
    match_relevant_paper,
)
from eval_harness.retrieval_online import (
    DEFAULT_DATASET_PATH,
    NativeProviderFetcher,
    evaluate_case_profile,
    resolve_snapshot_output_dir,
    run_online_benchmark,
    validate_snapshot_id,
    write_online_report,
)
import tools.arxiv_tool as arxiv_tool_module


def first_case_dataset():
    dataset = load_retrieval_dataset(DEFAULT_DATASET_PATH)
    return dataset.model_copy(update={"cases": dataset.cases[:1]})


def relevant_paper(source="arxiv", entry_id="2005.11401"):
    return {
        "title": "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks",
        "authors": ["Patrick Lewis"],
        "year": 2020,
        "summary": "RAG",
        "pdf_url": f"https://arxiv.org/pdf/{entry_id}",
        "entry_id": entry_id,
        "doi": "10.48550/arXiv.2005.11401",
        "source": source,
    }


def provider_result(provider, papers, *, success=True, error_code=""):
    return {
        "provider": provider,
        "success": success,
        "skipped": False,
        "error_code": error_code,
        "error_message": "failed" if error_code else "",
        "papers": papers,
        "attempt_count": 1,
        "network_latency_seconds": 0.2,
        "served_latency_seconds": 0.2,
        "cache_hit": False,
    }


def test_retrieval_dataset_loads_versioned_twenty_case_gold_standard():
    dataset = load_retrieval_dataset(DEFAULT_DATASET_PATH)

    assert dataset.dataset_version == "1.0.0"
    assert dataset.k_values == [1, 3, 5]
    assert len(dataset.cases) == 20
    assert len({case.id for case in dataset.cases}) == 20
    assert all(case.relevant_papers for case in dataset.cases)


def test_retrieval_dataset_rejects_duplicate_case_ids():
    dataset = first_case_dataset()
    payload = dataset.model_dump()
    payload["cases"].append(payload["cases"][0])

    with pytest.raises(ValidationError, match="case ids must be unique"):
        RetrievalEvalDataset.model_validate(payload)


def test_paper_identity_normalizes_doi_arxiv_id_and_title():
    paper = relevant_paper()

    assert normalize_doi("HTTPS://DOI.ORG/10.48550/ARXIV.2005.11401") == (
        "10.48550/arxiv.2005.11401"
    )
    assert extract_arxiv_id(paper["pdf_url"]) == "2005.11401"
    assert normalize_title("  Retrieval—Augmented  Generation! ") == (
        "retrieval augmented generation"
    )
    assert {
        "doi:10.48550/arxiv.2005.11401",
        "arxiv:2005.11401",
    }.issubset(paper_identity_keys(paper))


def test_gold_match_rejects_stable_identity_with_contradictory_title():
    case = first_case_dataset().cases[0]
    corrupted = relevant_paper()
    corrupted["title"] = "A Completely Different Paper About Robotics"

    assert match_relevant_paper(corrupted, case.relevant_papers) == (None, 0)


def test_ranking_metrics_calculate_recall_precision_mrr_ndcg_and_dimensions():
    case = first_case_dataset().cases[0]
    papers = [
        {"title": "Irrelevant Work", "entry_id": "other"},
        relevant_paper(),
    ]

    metrics = calculate_case_metrics(case, papers, [1, 3, 5])

    assert metrics["recall_at_1"] == 0.0
    assert metrics["recall_at_3"] == 1.0
    assert metrics["precision_at_3"] == 0.333333
    assert metrics["mrr_at_3"] == 0.5
    assert metrics["ndcg_at_3"] == 0.63093
    assert metrics["dimension_coverage_pct"] == 100.0
    assert metrics["first_relevant_rank"] == 2


def test_duplicate_rate_handles_zero_and_merged_counts():
    assert duplicate_rate(0, 0) == 0.0
    assert duplicate_rate(4, 3) == 25.0


def test_multi_profile_deduplicates_and_records_partial_provider_failure():
    case = first_case_dataset().cases[0]
    provider_results = {
        "arxiv": provider_result("arxiv", [], success=False, error_code="TIMEOUT"),
        "openalex": provider_result(
            "openalex",
            [relevant_paper(source="openalex", entry_id="https://openalex.org/W1")],
        ),
    }

    result = evaluate_case_profile(case, "multi", provider_results, [1, 3, 5])

    assert result["status"] == "partial_success"
    assert result["recall_at_1"] == 1.0
    assert result["provider_errors"][0]["error_code"] == "TIMEOUT"
    assert result["merged_document_count"] == 1


def test_successful_zero_result_is_empty_instead_of_failed():
    case = first_case_dataset().cases[0]
    result = evaluate_case_profile(
        case,
        "arxiv",
        {"arxiv": provider_result("arxiv", [])},
        [1, 3, 5],
    )

    assert result["status"] == "empty"
    assert result["provider_errors"] == []

    skipped_openalex = provider_result("openalex", [], success=False)
    skipped_openalex.update({"skipped": True, "error_code": "MISSING_API_KEY"})
    multi_result = evaluate_case_profile(
        case,
        "multi",
        {"arxiv": provider_result("arxiv", []), "openalex": skipped_openalex},
        [1, 3, 5],
    )
    assert multi_result["status"] == "empty"


def test_online_benchmark_reuses_provider_results_across_profiles():
    dataset = first_case_dataset()

    class FakeFetcher:
        def __init__(self):
            self.calls = []
            self.actual_api_call_count = 0
            self.cache_hit_count = 0

        def fetch(self, case, provider, max_results):
            self.calls.append((case.id, provider, max_results))
            self.actual_api_call_count += 1
            return provider_result(provider, [relevant_paper(source=provider)])

    fetcher = FakeFetcher()
    report = run_online_benchmark(
        dataset,
        fetcher,
        ["arxiv", "openalex", "multi"],
    )

    assert fetcher.calls == [
        (dataset.cases[0].id, "arxiv", 5),
        (dataset.cases[0].id, "openalex", 5),
    ]
    assert report["acquisition"]["actual_api_call_count"] == 2
    assert report["profiles"]["multi"]["summary"]["mean_recall_at_5"] == 1.0
    assert report["profiles"]["multi"]["cases"][0]["duplicate_rate_pct"] == 50.0


def test_verified_rerank_reports_quarantined_secondary_identity():
    case = first_case_dataset().cases[0]
    corrupted = relevant_paper(source="openalex", entry_id="https://openalex.org/W1")
    corrupted["title"] = "A Completely Different Paper About Robotics"
    provider_results = {
        "arxiv": provider_result("arxiv", []),
        "openalex": provider_result("openalex", [corrupted]),
    }

    result = evaluate_case_profile(
        case,
        "multi_verified_rerank",
        provider_results,
        [1, 3, 5],
    )

    assert result["returned_count"] == 0
    assert result["metadata_quarantined_count"] == 1
    assert result["quarantined_documents"][0]["canonical_identity"] == (
        "arxiv:2005.11401"
    )


def test_missing_openalex_key_is_explicitly_skipped_without_network(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "eval_harness.retrieval_online.settings.OPENALEX_API_KEY",
        "",
    )
    fetcher = NativeProviderFetcher(tmp_path)

    result = fetcher.fetch(first_case_dataset().cases[0], "openalex", 5)

    assert result["skipped"] is True
    assert result["error_code"] == "MISSING_API_KEY"
    assert fetcher.actual_api_call_count == 0


def test_arxiv_pacing_waits_only_for_remaining_interval(monkeypatch):
    fetcher = NativeProviderFetcher.__new__(NativeProviderFetcher)
    fetcher.arxiv_interval_seconds = 6.0
    fetcher._last_arxiv_request_at = 10.0
    waits = []
    monkeypatch.setattr("eval_harness.retrieval_online.time.monotonic", lambda: 12.5)
    monkeypatch.setattr("eval_harness.retrieval_online.time.sleep", waits.append)

    fetcher._wait_before_request("arxiv")
    fetcher._wait_before_request("openalex")

    assert waits == [3.5]
    assert fetcher._is_rate_limited("EXECUTION_ERROR", "Page returned HTTP 429")


def test_online_report_writes_json_summary_case_and_paper_tables(tmp_path):
    dataset = first_case_dataset()

    class FakeFetcher:
        actual_api_call_count = 1
        cache_hit_count = 0

        def fetch(self, case, provider, max_results):
            return provider_result(provider, [relevant_paper(source=provider)])

    report = run_online_benchmark(dataset, FakeFetcher(), ["arxiv"])
    path = write_online_report(report, tmp_path)

    assert json.loads(path.read_text(encoding="utf-8"))["dataset_case_count"] == 1
    assert (tmp_path / "latest_retrieval_summary.csv").exists()
    assert (tmp_path / "latest_retrieval_cases.csv").exists()
    assert (tmp_path / "latest_retrieval_papers.csv").exists()
    manifest = json.loads(
        (tmp_path / "snapshot_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["snapshot_id"] == "legacy"
    assert manifest["cumulative_acquisition"] == {
        "actual_api_call_count": 1,
        "provider_cache_hit_count": 0,
        "run_count": 1,
    }

    write_online_report(report, tmp_path)
    manifest = json.loads(
        (tmp_path / "snapshot_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["cumulative_acquisition"]["actual_api_call_count"] == 2
    assert manifest["cumulative_acquisition"]["run_count"] == 2


def test_snapshot_id_is_path_safe_and_uses_isolated_directory(tmp_path):
    assert validate_snapshot_id("2026-08-11_openalex-b") == (
        "2026-08-11_openalex-b"
    )
    assert resolve_snapshot_output_dir(tmp_path, "snapshot-b") == (
        tmp_path / "snapshots" / "snapshot-b"
    )
    assert resolve_snapshot_output_dir(tmp_path, "") == tmp_path

    for invalid in ("", "../escape", "nested/path", "含中文"):
        with pytest.raises(ValueError, match="snapshot id"):
            validate_snapshot_id(invalid)


def test_existing_snapshot_requires_explicit_resume(tmp_path):
    snapshot_dir = tmp_path / "snapshots" / "snapshot-b"
    snapshot_dir.mkdir(parents=True)
    (snapshot_dir / "existing.json").write_text("{}", encoding="utf-8")

    with pytest.raises(FileExistsError, match="resume-snapshot"):
        resolve_snapshot_output_dir(tmp_path, "snapshot-b")

    assert resolve_snapshot_output_dir(
        tmp_path,
        "snapshot-b",
        resume=True,
    ) == snapshot_dir


def test_arxiv_network_failure_propagates_to_tool_executor(monkeypatch):
    class BrokenClient:
        def __init__(self, *args, **kwargs):
            raise ConnectionError("offline")

    monkeypatch.setattr(arxiv_tool_module.arxiv, "Client", BrokenClient)

    with pytest.raises(ConnectionError, match="offline"):
        arxiv_tool_module.search_arxiv_papers("test", max_results=1)
