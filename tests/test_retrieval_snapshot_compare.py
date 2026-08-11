from eval_harness.retrieval_snapshot_compare import compare_snapshots


def report(snapshot_id, recall, quarantined_titles, *, failed=0):
    cases = [
        {
            "case_id": "case-1",
            "query": "paper query",
            "recall_at_5": recall,
            "mrr_at_5": recall,
            "ndcg_at_5": recall,
            "quarantined_documents": [
                {
                    "title": title,
                    "canonical_identity": f"arxiv:{title.casefold()}",
                    "source": "openalex",
                    "metadata_warnings": ["UNVERIFIED_ARXIV_ID_TITLE_MISMATCH"],
                }
                for title in quarantined_titles
            ],
        }
    ]
    summary = {
        "failed_count": failed,
        "partial_success_count": 0,
        "mean_recall_at_5": recall,
        "mean_mrr_at_5": recall,
        "mean_ndcg_at_5": recall,
    }
    return {
        "snapshot_id": snapshot_id,
        "dataset_version": "1.0.0",
        "profiles": {"multi_verified_rerank": {"summary": summary, "cases": cases}},
    }


def test_snapshot_comparison_passes_stable_complete_non_regressing_candidate():
    baseline = report("a", 0.5, ["stable"])
    candidate = report("b", 0.6, ["stable"])

    comparison = compare_snapshots(baseline, candidate)

    assert comparison["promotion_ready"] is True
    assert comparison["critical_regression_count"] == 0
    assert comparison["quarantine"]["jaccard_stability"] == 1.0


def test_snapshot_comparison_blocks_quality_or_quarantine_instability():
    baseline = report("a", 0.6, ["first", "stable"])
    candidate = report("b", 0.5, ["stable", "new"])

    comparison = compare_snapshots(baseline, candidate)

    assert comparison["promotion_ready"] is False
    assert comparison["critical_regression_count"] == 1
    assert comparison["quarantine"]["jaccard_stability"] == 0.333333
    assert comparison["promotion_blockers"] == [
        "QUALITY_REGRESSION",
        "QUARANTINE_INSTABILITY",
    ]
