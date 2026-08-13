import json

from eval_harness.local_rag_gated_hybrid_stability import analyze


def _run(latency, route="hybrid"):
    summary={"recall_at_1":.2,"recall_at_3":.4,"recall_at_5":.5,"mrr_at_5":.4,"ndcg_at_5":.45,"page_recall_at_5":.6,"page_ndcg_at_5":.5,"average_query_latency_ms":latency,"p95_query_latency_ms":latency*2}
    case={"results":[{"chunk_id":"c1","score":.1}]}
    return {"config":{"model":"m"},"cache":{"hit":True,"fingerprint":"f"},"warmup":{"query":"academic paper semantic retrieval warmup","count":2,"excluded_from_formal_timing":True},"gated_hybrid":{"summary":summary,"cases":[case]},"route_decisions":[{"id":"q1","route":route}]}


def test_gated_hybrid_stability_requires_deterministic_routes_and_rankings(tmp_path):
    paths=[]
    for index,latency in enumerate((100,110,90),1):
        path=tmp_path/f"run_{index}.json";path.write_text(json.dumps(_run(latency)),encoding="utf-8");paths.append(path)
    report=analyze(paths,tmp_path/"report.json")
    assert report["routes_equal"] is True
    assert report["top5_rankings_equal"] is True
    assert report["decision"]["stability_validated"] is True


def test_gated_hybrid_stability_rejects_route_drift(tmp_path):
    paths=[]
    for index,route in enumerate(("hybrid","hybrid","dense"),1):
        path=tmp_path/f"run_{index}.json";path.write_text(json.dumps(_run(100,route)),encoding="utf-8");paths.append(path)
    report=analyze(paths,tmp_path/"report.json")
    assert report["routes_equal"] is False
    assert report["decision"]["stability_validated"] is False
