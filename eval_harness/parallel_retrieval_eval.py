"""Deterministic latency and equivalence benchmark for source-level parallelism."""

from __future__ import annotations

import json
import statistics
import time
from pathlib import Path
from unittest.mock import patch

from core.config import settings
from nodes.retrieve import retrieve_by_query


def run_mode(parallel: bool, delay_seconds: float = 0.12) -> tuple[dict, float]:
    def fake_retrieve(query, state, source):
        time.sleep(delay_seconds)
        return {"papers": [{"title": f"{source} paper", "source": source, "entry_id": source}], "provider": source, "retrieval_source": source, "cache_hit": False, "tools_used": [source], "tool_execution": {}}
    started = time.perf_counter()
    with patch("nodes.retrieve.retrieve_from_source", side_effect=fake_retrieve), patch.object(settings, "RETRIEVAL_MODE", "multi"), patch.object(settings, "MULTI_SOURCE_PROVIDERS", "arxiv,openalex"), patch.object(settings, "MULTI_SOURCE_PARALLEL_ENABLED", parallel):
        result = retrieve_by_query("parallel benchmark", {})
    return result, round(time.perf_counter() - started, 6)


def _p95(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[round((len(ordered) - 1) * 0.95)]


def build_report(repetitions: int = 5) -> dict:
    serial_runs = []
    parallel_runs = []
    equality = []
    serial_titles = []
    parallel_titles = []
    for _ in range(repetitions):
        serial, serial_seconds = run_mode(False)
        parallel, parallel_seconds = run_mode(True)
        serial_runs.append(serial_seconds)
        parallel_runs.append(parallel_seconds)
        serial_titles = [row["title"] for row in serial["documents"]]
        parallel_titles = [row["title"] for row in parallel["documents"]]
        equality.append(serial_titles == parallel_titles)
    serial_seconds = statistics.median(serial_runs)
    parallel_seconds = statistics.median(parallel_runs)
    return {
        "repetitions": repetitions,
        "serial_runs_seconds": serial_runs,
        "parallel_runs_seconds": parallel_runs,
        "serial_median_seconds": round(serial_seconds, 6),
        "parallel_median_seconds": round(parallel_seconds, 6),
        "serial_p95_seconds": round(_p95(serial_runs), 6),
        "parallel_p95_seconds": round(_p95(parallel_runs), 6),
        "speedup": round(serial_seconds / parallel_seconds, 6),
        "latency_reduction_pct": round((serial_seconds - parallel_seconds) / serial_seconds * 100, 2),
        "result_order_equal": all(equality),
        "result_equality_rate": round(sum(equality) / len(equality), 6),
        "serial_titles": serial_titles,
        "parallel_titles": parallel_titles,
    }


if __name__ == "__main__":
    report = build_report()
    path = Path("eval_harness/reports/parallel_retrieval_eval.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
