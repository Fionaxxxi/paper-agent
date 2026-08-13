from eval_harness.local_rag_dense_compare import compare
from pathlib import Path


def test_dense_comparison_uses_holdout_quality_and_keeps_production_off(tmp_path):
    report = compare(Path("outputs/local_rag/dense_multilingual_minilm.json"), tmp_path / "compare.json")
    assert report["comparisons"]["holdout"]["metrics"]["recall_at_5"]["delta"] == 0.2
    assert report["comparisons"]["holdout"]["metrics"]["ndcg_at_5"]["delta"] > 0
    assert report["comparisons"]["holdout"]["outcomes"]["regressed"] == 3
    assert report["decision"]["promote_to_candidate"] is False
    assert report["decision"]["production_default"] is False
