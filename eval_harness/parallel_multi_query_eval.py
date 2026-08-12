"""Deterministic latency and equivalence benchmark for sub-query parallelism."""

from __future__ import annotations

import json
import statistics
import time
from pathlib import Path
from unittest.mock import patch

from core.config import settings
from nodes.retrieve import retrieve_multi_query

SUB_QUERIES = ["rag methods", "graphrag methods", "evaluation comparison"]


def _fake_result(query: str) -> dict:
    return {
        "documents": [{"entry_id": query, "title": query}],
        "retrieval_source": "arxiv",
        "search_query": query,
        "cache_hit_count": 0,
        "source_statuses": [{"provider": "arxiv"}],
        "tool_executions": [],
        "tools_used": ["arxiv"],
    }


def run_mode(parallel: bool, delay_seconds: float = 0.15) -> tuple[dict, float]:
    def fake_retrieve(query, state):
        time.sleep(delay_seconds)
        return _fake_result(query)

    started = time.perf_counter()
    with patch("nodes.retrieve.retrieve_by_query", side_effect=fake_retrieve), patch.object(
        settings, "MULTI_QUERY_PARALLEL_ENABLED", parallel
    ), patch.object(settings, "MULTI_QUERY_MAX_WORKERS", 2):
        result = retrieve_multi_query({}, SUB_QUERIES)
    return result, round(time.perf_counter() - started, 6)


def _p95(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[round((len(ordered) - 1) * 0.95)]


def build_report(repetitions: int = 5) -> dict:
    serial_runs, parallel_runs, equal = [], [], []
    serial_queries, parallel_queries = [], []
    for _ in range(repetitions):
        serial, serial_seconds = run_mode(False)
        parallel, parallel_seconds = run_mode(True)
        serial_runs.append(serial_seconds)
        parallel_runs.append(parallel_seconds)
        serial_queries = serial["paper_metadata"]["search_queries"]
        parallel_queries = parallel["paper_metadata"]["search_queries"]
        equal.append(serial_queries == parallel_queries == SUB_QUERIES and serial["documents"] == parallel["documents"])

    serial_median = statistics.median(serial_runs)
    parallel_median = statistics.median(parallel_runs)
    report = {
        "repetitions": repetitions,
        "sub_query_count": len(SUB_QUERIES),
        "max_workers": 2,
        "serial_runs_seconds": serial_runs,
        "parallel_runs_seconds": parallel_runs,
        "serial_median_seconds": round(serial_median, 6),
        "parallel_median_seconds": round(parallel_median, 6),
        "serial_p95_seconds": round(_p95(serial_runs), 6),
        "parallel_p95_seconds": round(_p95(parallel_runs), 6),
        "speedup": round(serial_median / parallel_median, 6),
        "latency_reduction_pct": round((serial_median - parallel_median) / serial_median * 100, 2),
        "result_equality_rate": round(sum(equal) / len(equal), 6),
        "planned_order_preserved": parallel_queries == SUB_QUERIES,
    }
    report["acceptance_passed"] = (
        report["speedup"] >= 1.3
        and report["latency_reduction_pct"] >= 20
        and report["result_equality_rate"] == 1.0
        and report["planned_order_preserved"]
    )
    return report


if __name__ == "__main__":
    report = build_report()
    path = Path("eval_harness/reports/parallel_multi_query_eval.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
