"""Small, auditable online A/B for serial versus parallel provider retrieval."""

from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path
from typing import Any, Callable
from unittest.mock import patch

from core.config import settings
from nodes.retrieve import retrieve_by_query

DEFAULT_QUERIES = [
    "retrieval augmented generation knowledge intensive NLP",
    "attention is all you need transformer architecture",
    "low rank adaptation parameter efficient fine tuning",
]


def _p95(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[round((len(ordered) - 1) * 0.95)]


def _identity(document: dict[str, Any]) -> str:
    return str(
        document.get("doi")
        or document.get("arxiv_id")
        or document.get("entry_id")
        or document.get("title")
        or ""
    ).strip().lower()


def _failure_codes(result: dict[str, Any]) -> list[str]:
    return [
        str(row.get("tool_error_code", ""))
        for row in result.get("tool_executions", [])
        if not row.get("tool_success", False)
    ]


def run_online_ab(
    queries: list[str],
    repetitions: int = 2,
    runner: Callable[[str, dict[str, Any]], dict[str, Any]] = retrieve_by_query,
) -> dict[str, Any]:
    """Run paired requests. Serial runs first to avoid flattering parallel mode."""
    if not queries or repetitions < 1:
        raise ValueError("queries must be non-empty and repetitions must be positive")

    rows: list[dict[str, Any]] = []
    for repetition in range(1, repetitions + 1):
        for query in queries:
            pair: dict[str, dict[str, Any]] = {}
            for mode, parallel in (("serial", False), ("parallel", True)):
                started = time.perf_counter()
                with patch.object(settings, "RETRIEVAL_MODE", "multi"), patch.object(
                    settings, "MULTI_SOURCE_PARALLEL_ENABLED", parallel
                ):
                    result = runner(query, {})
                elapsed = time.perf_counter() - started
                identities = [_identity(row) for row in result.get("documents", [])]
                pair[mode] = result
                rows.append(
                    {
                        "repetition": repetition,
                        "query": query,
                        "mode": mode,
                        "latency_seconds": round(elapsed, 6),
                        "paper_count": len(identities),
                        "identities": identities,
                        "providers": [row.get("provider", "") for row in result.get("source_statuses", [])],
                        "failure_codes": _failure_codes(result),
                    }
                )
            serial_ids = set(_identity(row) for row in pair["serial"].get("documents", []))
            parallel_ids = set(_identity(row) for row in pair["parallel"].get("documents", []))
            union = serial_ids | parallel_ids
            overlap = 1.0 if not union else len(serial_ids & parallel_ids) / len(union)
            rows[-2]["pair_overlap_rate"] = round(overlap, 6)
            rows[-1]["pair_overlap_rate"] = round(overlap, 6)

    serial = [row["latency_seconds"] for row in rows if row["mode"] == "serial"]
    parallel = [row["latency_seconds"] for row in rows if row["mode"] == "parallel"]
    overlaps = [row["pair_overlap_rate"] for row in rows if row["mode"] == "parallel"]
    serial_median = statistics.median(serial)
    parallel_median = statistics.median(parallel)
    all_failures = [code for row in rows for code in row["failure_codes"]]
    summary = {
        "query_count": len(queries),
        "repetitions": repetitions,
        "request_count": len(rows),
        "serial_p50_seconds": round(serial_median, 6),
        "parallel_p50_seconds": round(parallel_median, 6),
        "serial_p95_seconds": round(_p95(serial), 6),
        "parallel_p95_seconds": round(_p95(parallel), 6),
        "speedup": round(serial_median / parallel_median, 6) if parallel_median else 0,
        "latency_reduction_pct": round((serial_median - parallel_median) / serial_median * 100, 2) if serial_median else 0,
        "mean_result_overlap_rate": round(statistics.mean(overlaps), 6),
        "failure_count": len(all_failures),
        "rate_limited_count": sum(code == "RATE_LIMITED" for code in all_failures),
    }
    summary["acceptance_passed"] = (
        summary["parallel_p95_seconds"] <= summary["serial_p95_seconds"]
        and summary["mean_result_overlap_rate"] >= 0.95
        and summary["failure_count"] == 0
    )
    return {"mode": "online_native_tools", "summary": summary, "runs": rows}


def write_report(report: dict[str, Any], output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run bounded online serial/parallel retrieval A/B.")
    parser.add_argument("--repetitions", type=int, default=2)
    parser.add_argument("--query-limit", type=int, default=3)
    parser.add_argument("--output", type=Path, default=Path("eval_harness/reports/parallel_retrieval_online.json"))
    args = parser.parse_args()
    report = run_online_ab(DEFAULT_QUERIES[: args.query_limit], args.repetitions)
    print(write_report(report, args.output))
    print(json.dumps(report["summary"], ensure_ascii=False))
