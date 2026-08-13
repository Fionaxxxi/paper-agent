from eval_harness.local_rag_hybrid_eval import select_candidate


def _candidate(k,recall,ndcg,regressed,latency):
    return {"rrf_k":k,"development":{"summary":{"recall_at_5":recall,"ndcg_at_5":ndcg,"average_query_latency_ms":latency}},"development_outcomes":{"regressed":regressed}}


def test_hybrid_parameter_selection_uses_frozen_quality_first_order():
    candidates=[_candidate(20,.8,.7,1,100),_candidate(40,.9,.6,0,80),_candidate(60,.9,.7,2,120)]
    assert select_candidate(candidates)["rrf_k"] == 60
