import json

from eval_harness.local_rag_dense_model_compare import compare


def test_dense_model_comparison_prefers_quality_gain_without_excess_regression(tmp_path):
    def run(ndcg,rank,latency,model):
        summary={k:ndcg for k in ("recall_at_1","recall_at_3","recall_at_5","mrr_at_5","ndcg_at_5","page_recall_at_5","page_ndcg_at_5")};summary["average_query_latency_ms"]=latency
        split={"summary":summary,"cases":[{"id":"c1","first_relevant_rank":rank,"metrics":{"ndcg_at_5":ndcg}}]}
        return {"config":{"model":model},"development":split,"holdout":split}
    a,b=tmp_path/"a.json",tmp_path/"b.json";a.write_text(json.dumps(run(.5,2,10,"mini")),encoding="utf-8");b.write_text(json.dumps(run(.6,1,20,"mpnet")),encoding="utf-8")
    report=compare(a,b,tmp_path/"out.json")
    assert report["splits"]["holdout"]["metrics"]["ndcg_at_5"]["delta"]==.1
    assert report["decision"]["preferred_model"]=="mpnet"
    assert report["decision"]["production_default"] is False
