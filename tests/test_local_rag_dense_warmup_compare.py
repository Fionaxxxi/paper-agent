import json

from eval_harness.local_rag_dense_warmup_compare import compare


def test_warmup_comparison_requires_failed_before_and_passed_after(tmp_path):
    timing = {key: {"mean": mean, "cv": cv} for key in ("development_average_query_ms", "development_p95_query_ms", "holdout_average_query_ms", "holdout_p95_query_ms") for mean, cv in [(100, .6)]}
    before = {"models":["m"],"timing":timing,"decision":{"stability_validated":False}}
    after = {"models":["m"],"timing":{key:{"mean":80,"cv":.2} for key in timing},"quality_equal":True,"top5_rankings_equal":True,"scores_equal":True,"warmup_protocol_match":True,"decision":{"stability_validated":True}}
    a,b=tmp_path/"before.json",tmp_path/"after.json";a.write_text(json.dumps(before),encoding="utf-8");b.write_text(json.dumps(after),encoding="utf-8")
    report=compare(a,b,tmp_path/"report.json")
    assert report["metrics"]["holdout_average_query_ms"]["mean_change_pct"] == -20
    assert report["decision"]["warmup_explains_instability"] is True
    assert report["decision"]["next_step"] == "Dense + BM25 Hybrid 互补对照"
