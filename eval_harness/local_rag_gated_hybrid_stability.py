"""汇总门控 Hybrid 的独立进程结果，检查确定性与延迟稳定性。"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

from eval_harness.local_rag_dense_cache_compare import QUALITY_KEYS


def _cv(values: list[float]) -> float:
    mean = statistics.mean(values)
    return round(statistics.pstdev(values) / mean, 6) if mean else 0.0


def analyze(run_paths: list[Path], output_path: Path) -> dict:
    if len(run_paths) < 3:
        raise ValueError("gated hybrid stability evaluation requires at least three independent runs")
    runs = [json.loads(path.read_text(encoding="utf-8")) for path in run_paths]
    reference = runs[0]
    configs = [run["config"] for run in runs]
    config_equal = all(config == configs[0] for config in configs[1:])
    warmup_equal = all(run["warmup"] ["query"] == "academic paper semantic retrieval warmup" and run["warmup"]["count"] == 2 and run["warmup"]["excluded_from_formal_timing"] is True for run in runs)
    cache_equal = all(run["cache"]["hit"] for run in runs) and len({run["cache"]["fingerprint"] for run in runs}) == 1
    quality_equal = all(run["gated_hybrid"]["summary"][key] == reference["gated_hybrid"]["summary"][key] for run in runs[1:] for key in QUALITY_KEYS)
    rankings_equal = all(
        [result["chunk_id"] for result in case["results"]] == [result["chunk_id"] for result in reference["gated_hybrid"]["cases"][index]["results"]]
        for run in runs[1:] for index, case in enumerate(run["gated_hybrid"]["cases"])
    )
    scores_equal = all(
        [result["score"] for result in case["results"]] == [result["score"] for result in reference["gated_hybrid"]["cases"][index]["results"]]
        for run in runs[1:] for index, case in enumerate(run["gated_hybrid"]["cases"])
    )
    routes_equal = all(run["route_decisions"] == reference["route_decisions"] for run in runs[1:])
    average_values = [run["gated_hybrid"]["summary"]["average_query_latency_ms"] for run in runs]
    p95_values = [run["gated_hybrid"]["summary"]["p95_query_latency_ms"] for run in runs]
    timing = {
        "average_query_ms": {"values": average_values, "mean": round(statistics.mean(average_values), 4), "cv": _cv(average_values)},
        "p95_query_ms": {"values": p95_values, "mean": round(statistics.mean(p95_values), 4), "cv": _cv(p95_values)},
    }
    latency_stable = timing["average_query_ms"]["cv"] <= 0.5
    stability_validated = config_equal and warmup_equal and cache_equal and quality_equal and rankings_equal and scores_equal and routes_equal and latency_stable
    report = {
        "report_version": "1.0",
        "run_count": len(runs),
        "config_equal": config_equal,
        "warmup_protocol_equal": warmup_equal,
        "cache_equal": cache_equal,
        "quality_equal": quality_equal,
        "top5_rankings_equal": rankings_equal,
        "scores_equal": scores_equal,
        "routes_equal": routes_equal,
        "timing": timing,
        "quality": reference["gated_hybrid"]["summary"],
        "route_decisions": reference["route_decisions"],
        "decision": {"stability_validated": stability_validated, "latency_stable": latency_stable, "production_default": False},
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    paths = sorted(Path("outputs/local_rag/gated_hybrid_stability_runs").glob("run_*.json"))
    print(json.dumps(analyze(paths, Path("outputs/local_rag/gated_hybrid_stability.json")), ensure_ascii=False, indent=2))
