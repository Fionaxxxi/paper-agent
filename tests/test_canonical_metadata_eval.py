import json

from eval_harness.canonical_metadata_eval import (
    CanonicalArxivFetcher,
    collect_claimed_arxiv_ids,
    collect_quarantined_arxiv_ids,
    evaluate_promotion,
)


def test_collect_claimed_arxiv_ids_uses_secondary_provider_claims(tmp_path):
    snapshot = tmp_path / "snapshot-a"
    for provider, papers in (
        ("arxiv", []),
        (
            "openalex",
            [{"doi": "https://doi.org/10.48550/arxiv.2205.11916"}],
        ),
    ):
        path = snapshot / "provider_cache" / "1.0.0" / provider / "case-1.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"success": True, "papers": papers}), encoding="utf-8"
        )

    identities = collect_claimed_arxiv_ids([snapshot], "1.0.0", ["case-1"])

    assert identities == ["2205.11916"]


def test_canonical_fetcher_caches_successful_lookup(tmp_path):
    fetcher = CanonicalArxivFetcher(tmp_path)
    calls = []
    fetcher.router.resolve = lambda capability, source: "paper.lookup.arxiv"
    fetcher.executor.execute = lambda name, arguments: calls.append(arguments) or type(
        "Result",
        (),
        {
            "success": True,
            "error_code": "",
            "error_message": "",
            "data": {"paper": {"title": "Canonical", "source": "arxiv"}},
        },
    )()

    first = fetcher.fetch("2205.11916")
    second = fetcher.fetch("2205.11916")

    assert first == second
    assert calls == [{"identity": "2205.11916"}]
    assert fetcher.actual_api_call_count == 1
    assert fetcher.cache_hit_count == 1


def test_canonical_fetcher_does_not_reuse_failed_lookup(tmp_path):
    failed = tmp_path / "2205.11916.json"
    failed.write_text(
        json.dumps({"success": False, "paper": None}), encoding="utf-8"
    )
    fetcher = CanonicalArxivFetcher(tmp_path)
    calls = []
    fetcher.router.resolve = lambda capability, source: "paper.lookup.arxiv"
    fetcher.executor.execute = lambda name, arguments: calls.append(arguments) or type(
        "Result",
        (),
        {
            "success": False,
            "error_code": "EXECUTION_ERROR",
            "error_message": "temporary",
            "data": {},
        },
    )()

    assert fetcher.fetch("2205.11916") is None
    assert calls == [{"identity": "2205.11916"}]
    assert fetcher.cache_hit_count == 0


def test_collect_quarantined_arxiv_ids_limits_authority_experiment(tmp_path):
    snapshot = tmp_path / "snapshot-a"
    snapshot.mkdir()
    report = {
        "profiles": {
            "multi_verified_rerank": {
                "cases": [
                    {
                        "quarantined_documents": [
                            {"doi": "10.48550/arxiv.2205.11916"}
                        ]
                    }
                ]
            }
        }
    }
    (snapshot / "latest_retrieval_online.json").write_text(
        json.dumps(report), encoding="utf-8"
    )

    assert collect_quarantined_arxiv_ids([snapshot]) == ["2205.11916"]


def test_promotion_requires_three_complete_non_regressing_snapshots(tmp_path):
    snapshots = []
    candidates = []
    for index in range(3):
        snapshot = tmp_path / f"snapshot-{index}"
        snapshot.mkdir()
        baseline_case = {"case_id": "case-1", "recall_at_5": 0.5, "mrr_at_5": 0.5, "ndcg_at_5": 0.5}
        baseline_summary = {"failed_count": 0, "partial_success_count": 0, "mean_recall_at_5": 0.5, "mean_mrr_at_5": 0.5, "mean_ndcg_at_5": 0.5}
        (snapshot / "latest_retrieval_online.json").write_text(json.dumps({"profiles": {"multi_verified_rerank": {"summary": baseline_summary, "cases": [baseline_case]}}}), encoding="utf-8")
        snapshots.append(snapshot)
        candidates.append({"snapshot_id": snapshot.name, "summary": {"mean_recall_at_5": 0.6, "mean_mrr_at_5": 0.6, "mean_ndcg_at_5": 0.6}, "cases": [{**baseline_case, "recall_at_5": 0.6, "mrr_at_5": 0.6, "ndcg_at_5": 0.6}]})

    result = evaluate_promotion(snapshots, candidates, authority_identity_count=4, claimed_identity_count=4)

    assert result["promotion_ready"] is True
    assert result["quality_regression_count"] == 0
