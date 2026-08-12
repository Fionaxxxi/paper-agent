import json

from eval_harness.crossref_authority_eval import (
    collect_stable_ordinary_doi_claims,
    compare_providers,
    evaluate_claims,
    select_stratified_claims,
)


def test_collects_only_ordinary_dois_stable_across_all_snapshots(tmp_path):
    snapshots = []
    for index in range(2):
        snapshot = tmp_path / f"s{index}"
        snapshot.mkdir()
        report = {"snapshot_id": f"s{index}", "profiles": {"openalex": {"cases": [{"case_id": "c1", "ranked_papers": [{"doi": "10.1000/ordinary", "title": "Stable"}, {"doi": "10.48550/arxiv.2205.11916", "title": "arXiv"}]}]}}}
        (snapshot / "latest_retrieval_online.json").write_text(json.dumps(report), encoding="utf-8")
        snapshots.append(snapshot)

    claims = collect_stable_ordinary_doi_claims(snapshots)

    assert [row["doi"] for row in claims] == ["10.1000/ordinary"]


def test_crossref_eval_separates_match_conflict_not_found_and_failure():
    claims = [{"doi": str(i), "claimed_title": "Canonical Paper", "snapshots": [], "case_ids": []} for i in range(4)]
    payloads = {
        "0": {"success": True, "paper": {"title": "Canonical Paper"}},
        "1": {"success": True, "paper": {"title": "Entirely Different Work"}},
        "2": {"success": True, "paper": None},
        "3": {"success": False, "paper": None, "error_code": "TIMEOUT"},
    }
    fetcher = type("Fetcher", (), {"fetch": lambda self, doi: payloads[doi]})()

    result = evaluate_claims(claims, fetcher)

    assert (result["match_count"], result["title_conflict_count"], result["not_found_count"], result["failed_count"]) == (1, 1, 1, 1)


def test_stratified_sample_round_robins_doi_prefixes():
    claims = [
        {"doi": "10.1/a", "doi_prefix": "10.1"},
        {"doi": "10.1/b", "doi_prefix": "10.1"},
        {"doi": "10.2/a", "doi_prefix": "10.2"},
        {"doi": "10.3/a", "doi_prefix": "10.3"},
    ]

    selected = select_stratified_claims(claims, 3)

    assert {row["doi_prefix"] for row in selected} == {"10.1", "10.2", "10.3"}


def test_provider_comparison_counts_only_two_successful_titles():
    results = [
        {"provider": "a", "rows": [{"doi": "x", "status": "MATCH", "canonical_title": "Same Paper"}, {"doi": "y", "status": "FAILED", "canonical_title": ""}]},
        {"provider": "b", "rows": [{"doi": "x", "status": "MATCH", "canonical_title": "Same Paper"}, {"doi": "y", "status": "MATCH", "canonical_title": "Other"}]},
    ]

    comparison = compare_providers(results)

    assert comparison["comparable_count"] == 1
    assert comparison["title_agreement_rate"] == 1.0
