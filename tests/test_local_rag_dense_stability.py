import json

from eval_harness.local_rag_dense_stability import analyze


def _run(latency, model="model-v1"):
    summary={"recall_at_1":.1,"recall_at_3":.2,"recall_at_5":.3,"mrr_at_5":.2,"ndcg_at_5":.25,"page_recall_at_5":.4,"page_ndcg_at_5":.3,"average_query_latency_ms":latency,"p95_query_latency_ms":latency*2}
    split={"summary":summary,"cases":[{"results":[{"chunk_id":"c1","score":.9},{"chunk_id":"c2","score":.8}]}]}
    return {"config":{"model":model},"cache":{"hit":True,"fingerprint":"same"},"timing":{"model_load_ms":100,"cache_load_ms":5,"index_build_ms":2},"development":split,"holdout":split}


def test_dense_stability_requires_three_deterministic_warm_processes(tmp_path):
    paths=[]
    for index,latency in enumerate((10,11,9),1):
        path=tmp_path/f"run_{index}.json";path.write_text(json.dumps(_run(latency)),encoding="utf-8");paths.append(path)
    report=analyze(paths,tmp_path/"report.json","model-v1")
    assert report["quality_equal"] and report["top5_rankings_equal"] and report["scores_equal"]
    assert report["decision"]["stability_validated"] is True
    assert report["decision"]["production_default"] is False


def test_dense_stability_rejects_mixed_or_unexpected_models(tmp_path):
    paths=[]
    for index,model in enumerate(("model-v1","model-v1","other-model"),1):
        path=tmp_path/f"mixed_{index}.json";path.write_text(json.dumps(_run(10,model)),encoding="utf-8");paths.append(path)
    report=analyze(paths,tmp_path/"mixed.json","model-v1")
    assert report["model_match"] is False
    assert report["decision"]["stability_validated"] is False
    assert report["decision"]["next_step"] == "隔离首次查询预热后重新评测性能稳定性"
