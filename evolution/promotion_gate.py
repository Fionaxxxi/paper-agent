from __future__ import annotations

from evolution.models import PromotionDecision, Scorecard


def _pct_delta(candidate: float, baseline: float) -> float:
    return round(candidate - baseline, 4)


def _relative_delta(candidate: float, baseline: float) -> float:
    if baseline <= 0:
        return 0.0 if candidate <= 0 else 100.0
    return round((candidate - baseline) / baseline * 100, 4)


def evaluate_promotion(
    baseline: Scorecard,
    candidate: Scorecard,
    *,
    minimum_quality_gain_pct_points: float = 2.0,
    maximum_token_increase_pct: float = 10.0,
    maximum_latency_increase_pct: float = 15.0,
) -> PromotionDecision:
    blockers: list[str] = []
    warnings: list[str] = []
    baseline_ids, candidate_ids = set(baseline.case_ids), set(candidate.case_ids)
    if baseline_ids != candidate_ids:
        blockers.append("case_set_mismatch")
    common = sorted(baseline_ids & candidate_ids)
    regressed = [
        case_id for case_id in common
        if baseline.per_case_passed.get(case_id) is True
        and candidate.per_case_passed.get(case_id) is False
    ]
    if regressed:
        blockers.append("case_regression")
    quality_delta = _pct_delta(candidate.pass_rate_pct, baseline.pass_rate_pct)
    token_delta = _relative_delta(candidate.average_tokens, baseline.average_tokens)
    latency_delta = _relative_delta(candidate.p95_latency_seconds, baseline.p95_latency_seconds)
    if quality_delta < minimum_quality_gain_pct_points:
        blockers.append("insufficient_quality_gain")
    if candidate.critical_pass_rate_pct < baseline.critical_pass_rate_pct:
        blockers.append("critical_case_regression")
    if candidate.safety_pass_rate_pct < baseline.safety_pass_rate_pct:
        blockers.append("safety_regression")
    if candidate.provider_failure_count > baseline.provider_failure_count:
        blockers.append("provider_failure_increase")
    if token_delta > maximum_token_increase_pct:
        blockers.append("token_budget_exceeded")
    elif token_delta > 0:
        warnings.append("token_usage_increased")
    if latency_delta > maximum_latency_increase_pct:
        blockers.append("latency_budget_exceeded")
    elif latency_delta > 0:
        warnings.append("latency_increased")
    gate_passed = not blockers
    return PromotionDecision(
        status="eligible_for_human_approval" if gate_passed else "rejected",
        gate_passed=gate_passed,
        blockers=blockers,
        warnings=warnings,
        deltas={
            "pass_rate_pct_points": quality_delta,
            "critical_pass_rate_pct_points": _pct_delta(candidate.critical_pass_rate_pct, baseline.critical_pass_rate_pct),
            "safety_pass_rate_pct_points": _pct_delta(candidate.safety_pass_rate_pct, baseline.safety_pass_rate_pct),
            "average_tokens_pct": token_delta,
            "p95_latency_pct": latency_delta,
        },
        regressed_case_ids=regressed,
    )
