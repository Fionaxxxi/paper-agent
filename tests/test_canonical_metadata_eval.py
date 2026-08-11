import json

from eval_harness.canonical_metadata_eval import (
    CanonicalArxivFetcher,
    collect_claimed_arxiv_ids,
    collect_quarantined_arxiv_ids,
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
