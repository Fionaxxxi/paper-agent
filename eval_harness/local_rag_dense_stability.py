"""汇总多个独立进程的 Dense 热启动结果，评估质量、排名和延迟稳定性。"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

from eval_harness.local_rag_dense_cache_compare import QUALITY_KEYS


def _cv(values: list[float]) -> float:
    mean = statistics.mean(values)
    return round(statistics.pstdev(values) / mean, 6) if mean else 0.0


def analyze(run_paths: list[Path], output_path: Path, expected_model: str | None = None) -> dict:
    if len(run_paths) < 3:
        raise ValueError("stability evaluation requires at least three independent runs")
    runs = [json.loads(path.read_text(encoding="utf-8")) for path in run_paths]
    reference = runs[0]
    models = {run.get("config", {}).get("model") for run in runs}
    model_match = len(models) == 1 and (expected_model is None or models == {expected_model})
    warmup_protocols = {(run.get("warmup", {}).get("query"), run.get("warmup", {}).get("count"), run.get("warmup", {}).get("excluded_from_formal_timing")) for run in runs}
    warmup_protocol_match = len(warmup_protocols) == 1 and next(iter(warmup_protocols)) == ("academic paper semantic retrieval warmup", 2, True)
    quality_equal = all(run[split]["summary"][key] == reference[split]["summary"][key] for run in runs[1:] for split in ("development", "holdout") for key in QUALITY_KEYS)
    rankings_equal = all(
        [result["chunk_id"] for result in case["results"]] == [result["chunk_id"] for result in reference[split]["cases"][index]["results"]]
        for run in runs[1:] for split in ("development", "holdout") for index, case in enumerate(run[split]["cases"])
    )
    scores_equal = all(
        [result["score"] for result in case["results"]] == [result["score"] for result in reference[split]["cases"][index]["results"]]
        for run in runs[1:] for split in ("development", "holdout") for index, case in enumerate(run[split]["cases"])
    )
    series = {
        "model_load_ms": [run["timing"]["model_load_ms"] for run in runs],
        "cache_load_ms": [run["timing"]["cache_load_ms"] for run in runs],
        "index_build_ms": [run["timing"]["index_build_ms"] for run in runs],
        "development_average_query_ms": [run["development"]["summary"]["average_query_latency_ms"] for run in runs],
        "development_p95_query_ms": [run["development"]["summary"]["p95_query_latency_ms"] for run in runs],
        "holdout_average_query_ms": [run["holdout"]["summary"]["average_query_latency_ms"] for run in runs],
        "holdout_p95_query_ms": [run["holdout"]["summary"]["p95_query_latency_ms"] for run in runs],
    }
    timing = {name: {"values": values, "mean": round(statistics.mean(values), 4), "min": min(values), "max": max(values), "cv": _cv(values)} for name, values in series.items()}
    all_cache_hits = all(run["cache"]["hit"] for run in runs)
    latency_stable = timing["development_average_query_ms"]["cv"] <= .5 and timing["holdout_average_query_ms"]["cv"] <= .5 and max(series["index_build_ms"]) < 100
    stability_validated = model_match and warmup_protocol_match and all_cache_hits and quality_equal and rankings_equal and scores_equal and latency_stable
    next_step = "Dense + BM25 Hybrid 互补对照" if stability_validated else "隔离首次查询预热后重新评测性能稳定性"
    report = {"report_version":"1.2","run_count":len(runs),"models":sorted(model for model in models if model),"expected_model":expected_model,"model_match":model_match,"warmup_protocol_match":warmup_protocol_match,"warmup_runs":[run.get("warmup") for run in runs],"all_cache_hits":all_cache_hits,"fingerprint_count":len({run["cache"]["fingerprint"] for run in runs}),"quality_equal":quality_equal,"top5_rankings_equal":rankings_equal,"scores_equal":scores_equal,"timing":timing,"decision":{"stability_validated":stability_validated,"latency_stable":latency_stable,"production_default":False,"next_step":next_step}}
    output_path.parent.mkdir(parents=True,exist_ok=True);output_path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8");return report


if __name__ == "__main__":
    paths=sorted(Path("outputs/local_rag/mpnet_stability_runs").glob("run_*.json"));print(json.dumps(analyze(paths,Path("outputs/local_rag/mpnet_stability.json"),"sentence-transformers/paraphrase-multilingual-mpnet-base-v2"),ensure_ascii=False,indent=2))
