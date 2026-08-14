"""Deterministic baseline-versus-Replan evaluation against query-repair oracles."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from nodes.retrieval_replan import build_retrieval_replan


CASES = [
    {"id": "timeout", "query": "agent memory", "documents": [], "score": 0.0, "codes": ["TIMEOUT"], "expected_type": "transient_tool_failure", "oracle_query": "agent memory"},
    {"id": "network", "query": "tool agents", "documents": [], "score": 0.0, "codes": ["NETWORK_ERROR"], "expected_type": "transient_tool_failure", "oracle_query": "tool agents"},
    {"id": "empty_quoted", "query": '"GraphRAG" (academic)', "documents": [], "score": 0.0, "codes": [], "expected_type": "empty_results", "oracle_query": "GraphRAG academic research survey"},
    {"id": "empty_narrow", "query": '"LLM wiki"', "documents": [], "score": 0.0, "codes": [], "expected_type": "empty_results", "oracle_query": "LLM wiki research survey"},
    {"id": "low_relevance", "query": "reflection agents", "documents": [{"title": "weak"}], "score": 0.5, "codes": [], "expected_type": "low_relevance", "oracle_query": "reflection agents survey review"},
    {"id": "low_relevance_memory", "query": "agent long term memory", "documents": [{"title": "weak"}], "score": 0.4, "codes": [], "expected_type": "low_relevance", "oracle_query": "agent long term memory survey review"},
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
        baseline_oracle_match = baseline_query == case["oracle_query"]
        candidate_oracle_match = candidate_query == case["oracle_query"]
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
            "oracle_query": case["oracle_query"],
            "baseline_oracle_match": baseline_oracle_match,
            "candidate_oracle_match": candidate_oracle_match,
            "baseline_ineffective_retry": semantic_failure and baseline_query == case["query"],
            "candidate_ineffective_retry": semantic_failure and candidate_query == case["query"],
        })

    count = len(rows)
    semantic_count = sum(row["expected_failure_type"] != "transient_tool_failure" for row in rows)
    baseline_matches = sum(row["baseline_oracle_match"] for row in rows)
    candidate_matches = sum(row["candidate_oracle_match"] for row in rows)
    baseline_ineffective = sum(row["baseline_ineffective_retry"] for row in rows)
    candidate_ineffective = sum(row["candidate_ineffective_retry"] for row in rows)
    summary = {
        "case_count": count,
        "classification_accuracy_pct": round(sum(row["classification_passed"] for row in rows) / count * 100, 2),
        "baseline_oracle_query_match_rate_pct": round(baseline_matches / count * 100, 2),
        "candidate_oracle_query_match_rate_pct": round(candidate_matches / count * 100, 2),
        "oracle_match_delta_pct_points": round((candidate_matches - baseline_matches) / count * 100, 2),
        "baseline_ineffective_retry_rate_pct": round(baseline_ineffective / semantic_count * 100, 2),
        "candidate_ineffective_retry_rate_pct": round(candidate_ineffective / semantic_count * 100, 2),
        "llm_call_count": 0,
    }
    summary["acceptance_passed"] = (
        summary["classification_accuracy_pct"] == 100.0
        and summary["candidate_oracle_query_match_rate_pct"] >= 80.0
        and summary["oracle_match_delta_pct_points"] >= 40.0
        and summary["candidate_ineffective_retry_rate_pct"] == 0.0
    )
    return {"mode": "offline_deterministic", "summary": summary, "cases": rows}


def write_report(report: dict[str, Any]) -> tuple[Path, Path]:
    output_dir = Path("eval_harness/reports")
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "retrieval_replan_eval.json"
    csv_path = output_dir / "retrieval_replan_eval.csv"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    with csv_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(report["cases"][0]))
        writer.writeheader()
        writer.writerows(report["cases"])
    return json_path, csv_path


if __name__ == "__main__":
    report = build_report()
    json_path, csv_path = write_report(report)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"JSON: {json_path.resolve()}")
    print(f"CSV: {csv_path.resolve()}")
