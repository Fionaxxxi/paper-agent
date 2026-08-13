import json

from eval_harness.local_rag_dense_cache_compare import compare


def test_dense_cache_comparison_requires_same_quality_and_faster_warm_build(tmp_path):
    summary = {"recall_at_1": .1, "recall_at_3": .2, "recall_at_5": .3, "mrr_at_5": .2, "ndcg_at_5": .25, "page_recall_at_5": .4, "page_ndcg_at_5": .3}
    base = {"cache": {"hit": False, "fingerprint": "same"}, "timing": {"index_build_ms": 1000, "cache_load_ms": 0}, "development": {"summary": summary}, "holdout": {"summary": summary}}
    warm = {**base, "cache": {"hit": True, "fingerprint": "same"}, "timing": {"index_build_ms": 2, "cache_load_ms": 5}}
    cold_path, warm_path = tmp_path / "cold.json", tmp_path / "warm.json"
    cold_path.write_text(json.dumps(base), encoding="utf-8"); warm_path.write_text(json.dumps(warm), encoding="utf-8")
    report = compare(cold_path, warm_path, tmp_path / "report.json")
    assert report["quality_equal"] is True
    assert report["decision"]["cache_validated"] is True
    assert report["decision"]["production_default"] is False
