import nodes.evaluate as evaluate_module


def test_first_low_score_requests_replan(monkeypatch):
    monkeypatch.setattr(evaluate_module, "rule_based_score", lambda state: 0.5)
    result = evaluate_module.evaluate_node({"retry_count": 0})
    assert result["retrieval_outcome"] == "replan_required"
    assert result["retrieval_stop_reason"] == "quality_below_threshold"


def test_second_low_score_stops_when_retry_budget_is_exhausted(monkeypatch):
    monkeypatch.setattr(evaluate_module, "rule_based_score", lambda state: 0.5)
    result = evaluate_module.evaluate_node({"retry_count": 1})
    assert result["retrieval_outcome"] == "stopped_low_quality"
    assert result["retrieval_stop_reason"] == "retry_budget_exhausted"


def test_second_high_score_records_recovery(monkeypatch):
    monkeypatch.setattr(evaluate_module, "rule_based_score", lambda state: 0.8)
    result = evaluate_module.evaluate_node({"retry_count": 1})
    assert result["retrieval_outcome"] == "recovered"
    assert result["retrieval_stop_reason"] == "quality_threshold_met"
