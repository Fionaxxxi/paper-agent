from eval_harness.local_rag_hybrid_eval import _outcomes


def test_gated_v2_outcomes_count_improvements_regressions_and_unchanged():
    def report(values): return {"cases":[{"id":key,"metrics":{"ndcg_at_5":value}} for key,value in values.items()]}
    outcomes=_outcomes(report({"a":0,"b":1,"c":.5}),report({"a":1,"b":0,"c":.5}))
    assert (outcomes["improved"],outcomes["regressed"],outcomes["unchanged"])==(1,1,1)
