from pathlib import Path

from eval_harness.local_rag_rewrite_ab import run_ab


def test_holdout_ab_detects_rank_regression_when_recall_at_five_is_unchanged(tmp_path):
    report = run_ab(
        tmp_path / "holdout.json",
        Path("eval_harness/datasets/rag_holdout_v1.json"),
        "test",
    )
    assert report["comparison"]["recall_at_5"]["delta"] == 0
    assert report["comparison"]["ndcg_at_5"]["delta"] < 0
    assert report["outcomes"]["regressed"] > 0
