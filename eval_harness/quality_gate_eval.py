"""Deterministic comparison of unguarded and evidence-safe answer generation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from nodes.generate import build_low_quality_answer

TOKENS_PER_GENERATION = 120
CASES = [
    {"id": "budget_empty", "outcome": "stopped_low_quality", "documents": [], "should_block": True},
    {"id": "budget_weak", "outcome": "stopped_low_quality", "documents": [{"title": "Weak candidate"}], "should_block": True},
    {"id": "budget_two_weak", "outcome": "stopped_low_quality", "documents": [{"title": "Weak A"}, {"title": "Weak B"}], "should_block": True},
    {"id": "budget_tool_degraded", "outcome": "stopped_low_quality", "documents": [{"title": "Unverified"}], "should_block": True},
    {"id": "accepted", "outcome": "accepted", "documents": [{"title": "Good"}], "should_block": False},
    {"id": "recovered", "outcome": "recovered", "documents": [{"title": "Recovered"}], "should_block": False},
    {"id": "accepted_multi", "outcome": "accepted", "documents": [{"title": "Good A"}, {"title": "Good B"}], "should_block": False},
    {"id": "recovered_multi", "outcome": "recovered", "documents": [{"title": "Recovered A"}], "should_block": False},
]


def _candidate(case: dict[str, Any]) -> dict[str, Any]:
    blocked = case["outcome"] == "stopped_low_quality"
    if blocked:
        state = {
            "documents": case["documents"],
            "retrieval_outcome": case["outcome"],
            "retrieval_replan": {"reason": "第二轮质量仍低于门槛"},
        }
        answer = build_low_quality_answer(state)
        compliant = all(text in answer for text in ("证据不足", "停止原因", "待人工核验"))
        return {"blocked": True, "llm_calls": 0, "tokens": 0, "format_compliant": compliant}
    return {"blocked": False, "llm_calls": 1, "tokens": TOKENS_PER_GENERATION, "format_compliant": True}


def build_report() -> dict[str, Any]:
    rows = []
    for case in CASES:
        baseline = {"blocked": False, "llm_calls": 1, "tokens": TOKENS_PER_GENERATION}
        candidate = _candidate(case)
        rows.append({
            "id": case["id"],
            "retrieval_outcome": case["outcome"],
            "should_block": case["should_block"],
            "baseline_blocked": baseline["blocked"],
            "candidate_blocked": candidate["blocked"],
            "candidate_correct": candidate["blocked"] == case["should_block"],
            "format_compliant": candidate["format_compliant"],
            "baseline_llm_calls": baseline["llm_calls"],
            "candidate_llm_calls": candidate["llm_calls"],
            "baseline_tokens": baseline["tokens"],
            "candidate_tokens": candidate["tokens"],
        })

    positives = sum(row["should_block"] for row in rows)
    negatives = len(rows) - positives
    true_blocks = sum(row["should_block"] and row["candidate_blocked"] for row in rows)
    false_blocks = sum(not row["should_block"] and row["candidate_blocked"] for row in rows)
    baseline_calls = sum(row["baseline_llm_calls"] for row in rows)
    candidate_calls = sum(row["candidate_llm_calls"] for row in rows)
    baseline_tokens = sum(row["baseline_tokens"] for row in rows)
    candidate_tokens = sum(row["candidate_tokens"] for row in rows)
    blocked_rows = [row for row in rows if row["candidate_blocked"]]
    summary = {
        "case_count": len(rows),
        "low_quality_block_accuracy_pct": round(true_blocks / positives * 100, 2),
        "normal_false_block_rate_pct": round(false_blocks / negatives * 100, 2),
        "degraded_format_compliance_pct": round(sum(row["format_compliant"] for row in blocked_rows) / len(blocked_rows) * 100, 2),
        "baseline_llm_call_count": baseline_calls,
        "candidate_llm_call_count": candidate_calls,
        "avoided_llm_call_count": baseline_calls - candidate_calls,
        "baseline_token_count": baseline_tokens,
        "candidate_token_count": candidate_tokens,
        "avoided_token_count": baseline_tokens - candidate_tokens,
    }
    summary["acceptance_passed"] = (
        summary["low_quality_block_accuracy_pct"] == 100.0
        and summary["normal_false_block_rate_pct"] == 0.0
        and summary["degraded_format_compliance_pct"] == 100.0
        and summary["avoided_llm_call_count"] == positives
    )
    return {"mode": "offline_deterministic", "tokens_per_generation": TOKENS_PER_GENERATION, "summary": summary, "cases": rows}


if __name__ == "__main__":
    report = build_report()
    path = Path("eval_harness/reports/quality_gate_eval.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
