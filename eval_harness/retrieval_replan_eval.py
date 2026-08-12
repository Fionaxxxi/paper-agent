"""Deterministic baseline-versus-Replan evaluation for retrieval recovery."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from nodes.retrieval_replan import build_retrieval_replan


CASES = [
    {"id": "timeout", "query": "agent memory", "documents": [], "score": 0.0, "codes": ["TIMEOUT"], "expected_type": "transient_tool_failure", "successful_query": "agent memory"},
    {"id": "network", "query": "tool agents", "documents": [], "score": 0.0, "codes": ["NETWORK_ERROR"], "expected_type": "transient_tool_failure", "successful_query": "tool agents"},
    {"id": "empty_quoted", "query": '"GraphRAG" (academic)', "documents": [], "score": 0.0, "codes": [], "expected_type": "empty_results", "successful_query": "GraphRAG academic research survey"},
    {"id": "empty_narrow", "query": '"LLM wiki"', "documents": [], "score": 0.0, "codes": [], "expected_type": "empty_results", "successful_query": "LLM wiki research survey"},
    {"id": "low_relevance", "query": "reflection agents", "documents": [{"title": "weak"}], "score": 0.5, "codes": [], "expected_type": "low_relevance", "successful_query": "reflection agents survey review"},
    {"id": "low_relevance_memory", "query": "agent long term memory", "documents": [{"title": "weak"}], "score": 0.4, "codes": [], "expected_type": "low_relevance", "successful_query": "agent long term memory survey review"},
]


def _state(case: dict[str, Any]) -> dict[str, Any]:
    executions = [
        {"tool_success": False, "tool_error_code": code} for code in case["codes"]
    ]
    return {
        "query": case["query"],
        "documents": case["documents"],
        "retrieval_score": case["score"],
        "retry_count": 0,
        "paper_metadata": {"search_query": case["query"], "tool_executions": executions},
    }


def build_report() -> dict[str, Any]:
    rows = []
    for case in CASES:
        baseline_query = case["query"]
        replan = build_retrieval_replan(_state(case))
        candidate_query = replan["retry_query"]
        baseline_recovered = baseline_query == case["successful_query"]
        candidate_recovered = candidate_query == case["successful_query"]
        classified = replan["retrieval_replan"]["failure_type"] == case["expected_type"]
        semantic_failure = case["expected_type"] != "transient_tool_failure"
        rows.append({
            "id": case["id"],
            "expected_failure_type": case["expected_type"],
            "actual_failure_type": replan["retrieval_replan"]["failure_type"],
            "action": replan["retrieval_replan"]["action"],
            "baseline_query": baseline_query,
            "candidate_query": candidate_query,
            "classification_passed": classified,
            "baseline_recovered": baseline_recovered,
            "candidate_recovered": candidate_recovered,
            "baseline_ineffective_retry": semantic_failure and baseline_query == case["query"],
            "candidate_ineffective_retry": semantic_failure and candidate_query == case["query"],
        })

    count = len(rows)
    semantic_count = sum(row["expected_failure_type"] != "transient_tool_failure" for row in rows)
    baseline_recovered = sum(row["baseline_recovered"] for row in rows)
    candidate_recovered = sum(row["candidate_recovered"] for row in rows)
    baseline_ineffective = sum(row["baseline_ineffective_retry"] for row in rows)
    candidate_ineffective = sum(row["candidate_ineffective_retry"] for row in rows)
    summary = {
        "case_count": count,
        "classification_accuracy_pct": round(sum(row["classification_passed"] for row in rows) / count * 100, 2),
        "baseline_recovery_rate_pct": round(baseline_recovered / count * 100, 2),
        "candidate_recovery_rate_pct": round(candidate_recovered / count * 100, 2),
        "recovery_rate_delta_pct_points": round((candidate_recovered - baseline_recovered) / count * 100, 2),
        "baseline_ineffective_retry_rate_pct": round(baseline_ineffective / semantic_count * 100, 2),
        "candidate_ineffective_retry_rate_pct": round(candidate_ineffective / semantic_count * 100, 2),
        "llm_call_count": 0,
    }
    summary["acceptance_passed"] = (
        summary["classification_accuracy_pct"] == 100.0
        and summary["candidate_recovery_rate_pct"] >= 80.0
        and summary["recovery_rate_delta_pct_points"] >= 40.0
        and summary["candidate_ineffective_retry_rate_pct"] == 0.0
    )
    return {"mode": "offline_deterministic", "summary": summary, "cases": rows}


if __name__ == "__main__":
    report = build_report()
    path = Path("eval_harness/reports/retrieval_replan_eval.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
