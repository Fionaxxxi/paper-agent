"""将多语言 Dense 与同数据集原始 BM25 做逐题对照。"""

from __future__ import annotations

import json
from pathlib import Path

from eval_harness.local_rag_benchmark import run_benchmark


def compare(dense_path: Path, output_path: Path) -> dict:
    dense = json.loads(dense_path.read_text(encoding="utf-8"))
    comparisons = {}
    for split, dataset_path in (("development", Path("eval_harness/datasets/rag_gold_v1.json")), ("holdout", Path("eval_harness/datasets/rag_holdout_v1.json"))):
        bm25 = run_benchmark(Path("data/papers"), dataset_path, output_path.parent / f"bm25_{split}_for_dense.json")
        dense_split = dense[split]
        cases = []
        for before, after in zip(bm25["cases"], dense_split["cases"]):
            delta = round(after["metrics"]["ndcg_at_5"] - before["metrics"]["ndcg_at_5"], 6)
            cases.append({"id": before["id"], "bm25_first_rank": before["first_relevant_rank"], "dense_first_rank": after["first_relevant_rank"], "bm25_recall_at_5": before["metrics"]["recall_at_5"], "dense_recall_at_5": after["metrics"]["recall_at_5"], "recall_delta": round(after["metrics"]["recall_at_5"] - before["metrics"]["recall_at_5"], 6), "ndcg_delta": delta, "outcome": "improved" if delta > 0 else "regressed" if delta < 0 else "unchanged"})
        metrics = {}
        for key in ("recall_at_1", "recall_at_3", "recall_at_5", "mrr_at_5", "ndcg_at_5", "page_recall_at_5", "page_ndcg_at_5"):
            metrics[key] = {"bm25": bm25["summary"][key], "dense": dense_split["summary"][key], "delta": round(dense_split["summary"][key] - bm25["summary"][key], 6)}
        comparisons[split] = {"metrics": metrics, "outcomes": {name: sum(case["outcome"] == name for case in cases) for name in ("improved", "regressed", "unchanged")}, "bm25_latency_ms": bm25["summary"]["average_query_latency_ms"], "dense_latency_ms": dense_split["summary"]["average_query_latency_ms"], "cases": cases}
    holdout = comparisons["holdout"]
    decision = {"promote_to_candidate": holdout["metrics"]["recall_at_5"]["delta"] >= 0.1 and holdout["metrics"]["ndcg_at_5"]["delta"] > 0 and holdout["outcomes"]["regressed"] <= 2, "production_default": False, "reason": "Dense 仅进入下一轮候选；仍需重复运行、索引缓存和第二模型对照。"}
    report = {"report_version": "1.0", "dense_config": dense["config"], "dense_timing": dense["timing"], "comparisons": comparisons, "decision": decision}
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"); return report


if __name__ == "__main__":
    result=compare(Path("outputs/local_rag/dense_multilingual_minilm.json"),Path("outputs/local_rag/dense_multilingual_compare.json")); print(json.dumps(result["decision"],ensure_ascii=False)); print(json.dumps(result["comparisons"]["holdout"],ensure_ascii=False)[:4000])
