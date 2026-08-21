import json

import pytest

from evolution.candidate_generator import generate_candidates
from evolution.adapters import analyzer_ab_scorecards, analyzer_baseline_failures
from evolution.failure_dataset import build_failure_dataset
from evolution.models import Scorecard
from evolution.promotion_gate import evaluate_promotion
from evolution.pipeline import run_evolution_cycle
from evolution.registry import StrategyVersionRegistry


def _scorecard(version: str, *, rate: float, tokens: float = 100, latency: float = 1, cases=None):
    cases = cases or {"a": True, "b": False}
    return Scorecard(
        version=version, case_ids=list(cases), pass_rate_pct=rate,
        average_tokens=tokens, p95_latency_seconds=latency,
        per_case_passed=cases,
    )


def test_failure_dataset_classifies_and_deduplicates_failed_cases(tmp_path):
    path = tmp_path / "failures.json"
    path.write_text(json.dumps({"cases": [{"id": "x", "passed": False, "failure_types": ["citation_missing", "citation_missing"]}]}), encoding="utf-8")
    dataset = build_failure_dataset([path])
    assert dataset.summary["failure_count"] == 1
    assert dataset.records[0].module == "citation_validation"


def test_candidate_generator_only_emits_allowlisted_non_applying_changes(tmp_path):
    path = tmp_path / "failures.json"
    path.write_text(json.dumps({"cases": [{"id": "x", "passed": False, "failure_type": "source_coverage_missing"}]}), encoding="utf-8")
    candidates = generate_candidates(build_failure_dataset([path]))
    assert candidates[0].target_module == "research_coverage"
    assert candidates[0].requires_human_approval is True
    assert candidates[0].auto_apply is False


def test_promotion_gate_accepts_quality_gain_without_regression():
    baseline = _scorecard("base", rate=50, cases={"a": True, "b": False})
    candidate = _scorecard("candidate", rate=100, tokens=105, latency=1.1, cases={"a": True, "b": True})
    decision = evaluate_promotion(baseline, candidate)
    assert decision.status == "eligible_for_human_approval"
    assert decision.gate_passed is True
    assert decision.auto_applied is False


def test_promotion_gate_rejects_case_regression_even_when_average_improves():
    baseline = _scorecard("base", rate=50, cases={"a": True, "b": False, "c": False})
    candidate = _scorecard("candidate", rate=66.7, cases={"a": False, "b": True, "c": True})
    decision = evaluate_promotion(baseline, candidate)
    assert "case_regression" in decision.blockers
    assert decision.status == "rejected"


def test_promotion_gate_rejects_cost_or_latency_budget_overrun():
    baseline = _scorecard("base", rate=50)
    candidate = _scorecard("candidate", rate=75, tokens=120, latency=1.2, cases={"a": True, "b": True})
    decision = evaluate_promotion(baseline, candidate)
    assert {"token_budget_exceeded", "latency_budget_exceeded"} <= set(decision.blockers)


def test_promotion_gate_rejects_mismatched_case_set():
    decision = evaluate_promotion(
        _scorecard("base", rate=50, cases={"a": True, "b": False}),
        _scorecard("candidate", rate=100, cases={"a": True}),
    )
    assert "case_set_mismatch" in decision.blockers


def test_registry_is_append_only_and_never_changes_active_version(tmp_path):
    registry = StrategyVersionRegistry(tmp_path / "registry.json")
    payload = registry.register({"version": "candidate-v1", "status": "eligible_for_human_approval"})
    assert payload["active_version"] == "baseline"
    assert payload["versions"][0]["auto_applied"] is False
    with pytest.raises(ValueError):
        registry.register({"version": "candidate-v1", "status": "rejected"})


def test_evolution_cycle_is_repeatable_and_does_not_auto_promote(tmp_path):
    failures = tmp_path / "failures.json"
    failures.write_text(json.dumps({"cases": [{"id": "b", "passed": False, "failure_type": "citation_missing"}]}), encoding="utf-8")
    scorecards = tmp_path / "scorecards.json"
    scorecards.write_text(json.dumps({
        "baseline": _scorecard("base", rate=50).model_dump(mode="json"),
        "candidate": _scorecard("candidate", rate=100, cases={"a": True, "b": True}).model_dump(mode="json"),
    }), encoding="utf-8")
    arguments = {
        "failure_sources": [failures], "scorecards_path": scorecards,
        "output_dir": tmp_path / "out", "registry_path": tmp_path / "registry.json",
    }
    first = run_evolution_cycle(**arguments)
    second = run_evolution_cycle(**arguments)
    assert first["registry_status"] == "registered"
    assert second["registry_status"] == "already_registered"
    assert first["promotion_decision"]["auto_applied"] is False


def test_analyzer_ab_adapter_preserves_per_case_regression_and_real_costs():
    report = {"dataset_version": "1", "variants": [
        {"variant": "zero_shot", "pass_rate_pct": 50, "token_usage": 200,
         "rows": [{"id": "a", "passed": True, "latency_seconds": 1, "checks": {}}, {"id": "b", "passed": False, "latency_seconds": 2, "checks": {"objective_coverage": False}}]},
        {"variant": "few_shot", "pass_rate_pct": 50, "token_usage": 300,
         "rows": [{"id": "a", "passed": False, "latency_seconds": 2, "checks": {}}, {"id": "b", "passed": True, "latency_seconds": 3, "checks": {}}]},
    ]}
    baseline, candidate = analyzer_ab_scorecards(report)
    assert baseline.average_tokens == 100
    assert candidate.average_tokens == 150
    assert baseline.per_case_passed["a"] is True
    assert candidate.per_case_passed["a"] is False
    failures = analyzer_baseline_failures(report)
    assert failures["cases"][0]["failure_types"] == ["objective_coverage"]
