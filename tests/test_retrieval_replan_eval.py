from eval_harness.retrieval_replan_eval import build_report


def test_replan_outperforms_plain_retry_and_meets_acceptance_gate():
    report = build_report()
    summary = report["summary"]

    assert summary["classification_accuracy_pct"] == 100.0
    assert summary["candidate_recovery_rate_pct"] == 100.0
    assert summary["baseline_recovery_rate_pct"] < summary["candidate_recovery_rate_pct"]
    assert summary["candidate_ineffective_retry_rate_pct"] == 0.0
    assert summary["llm_call_count"] == 0
    assert summary["acceptance_passed"] is True
