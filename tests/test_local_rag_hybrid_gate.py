from eval_harness.local_rag_hybrid_gate import GateRule, audit_rules, extract_features


def test_gate_features_use_only_runtime_rankings_and_scores():
    dense={"results":[{"chunk_id":"a","score":.8},{"chunk_id":"b","score":.7},{"chunk_id":"c","score":.6},{"chunk_id":"d","score":.5},{"chunk_id":"e","score":.4}]}
    bm25={"results":[{"chunk_id":"a"},{"chunk_id":"x"},{"chunk_id":"c"},{"chunk_id":"y"},{"chunk_id":"z"}]}
    assert extract_features(dense,bm25)=={"dense_top1":.8,"dense_margin":.1,"top5_overlap":.4}


def test_gate_audit_rejects_rules_with_regression_or_insufficient_gain():
    rule=GateRule(1,1,0);rows=[{"features":{"dense_top1":.5,"dense_margin":.1,"top5_overlap":.2},"outcome":x} for x in ("improved","regressed","unchanged")]
    result=audit_rules(rows,[rule])
    assert result["gate_learnable"] is False
    assert result["candidates"][0]["regressed"] == 1
