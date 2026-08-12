from eval_harness.quality_gate_eval import build_report


def test_quality_gate_blocks_low_quality_without_false_blocks_or_llm_cost():
    summary = build_report()["summary"]

    assert summary["low_quality_block_accuracy_pct"] == 100.0
    assert summary["normal_false_block_rate_pct"] == 0.0
    assert summary["degraded_format_compliance_pct"] == 100.0
    assert summary["avoided_llm_call_count"] == 4
    assert summary["avoided_token_count"] == 480
    assert summary["acceptance_passed"] is True
