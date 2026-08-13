import json

from eval_harness.local_rag_dense_stability_compare import compare


def test_stability_comparison_preserves_failed_candidate_decision(tmp_path):
    timing={"holdout_average_query_ms":{"mean":10,"cv":.1}}
    base={"timing":timing,"quality_equal":True,"top5_rankings_equal":True,"scores_equal":True,"decision":{"stability_validated":True}}
    candidate={**base,"timing":{"holdout_average_query_ms":{"mean":20,"cv":.6}},"decision":{"stability_validated":False}}
    a,b=tmp_path/"a.json",tmp_path/"b.json";a.write_text(json.dumps(base),encoding="utf-8");b.write_text(json.dumps(candidate),encoding="utf-8")
    report=compare(a,b,tmp_path/"out.json")
    assert report["metrics"]["holdout_average_query_ms"]["mean_ratio"]==2
    assert report["decision"]["mpnet_stability_validated"] is False
    assert report["decision"]["production_default"] is False
