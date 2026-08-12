"""同一冻结开发集上的原始 BM25 与确定性查询扩展 A/B。"""

from __future__ import annotations

import json
from pathlib import Path

from eval_harness.local_rag_benchmark import run_benchmark
from local_rag.query_rewrite import TERM_MAP, expand_query


def run_ab(output_path: Path) -> dict:
    root, dataset = Path("data/papers"), Path("eval_harness/datasets/rag_gold_v1.json")
    baseline = run_benchmark(root, dataset, output_path.parent / "bm25_ab_baseline.json")
    candidate = run_benchmark(root, dataset, output_path.parent / "bm25_rewrite_candidate.json", expand_query, "bm25-rewrite-v1")
    cases = []
    for before, after in zip(baseline["cases"], candidate["cases"]):
        delta = after["metrics"]["recall_at_5"] - before["metrics"]["recall_at_5"]
        cases.append({"id": before["id"], "question": before["question"], "search_query": after["search_query"], "rewrite_matches": after["rewrite_matches"], "baseline_first_rank": before["first_relevant_rank"], "candidate_first_rank": after["first_relevant_rank"], "baseline_recall_at_5": before["metrics"]["recall_at_5"], "candidate_recall_at_5": after["metrics"]["recall_at_5"], "chunk_recall_delta": delta, "page_recall_delta": after["page_metrics"]["recall_at_5"] - before["page_metrics"]["recall_at_5"], "outcome": "improved" if delta > 0 else "regressed" if delta < 0 else "unchanged"})
    metrics = [f"{prefix}{metric}_at_{k}" for prefix in ("", "page_") for k in (1, 3, 5) for metric in ("recall", "mrr", "ndcg")]
    comparison = {key: {"baseline": baseline["summary"][key], "candidate": candidate["summary"][key], "delta": round(candidate["summary"][key] - baseline["summary"][key], 6)} for key in metrics}
    report = {"report_version": "1.0", "evaluation_role": "development_ab_not_promotion_evidence", "term_map": TERM_MAP, "baseline": baseline["summary"], "candidate": candidate["summary"], "comparison": comparison, "outcomes": {"improved": sum(x["outcome"] == "improved" for x in cases), "regressed": sum(x["outcome"] == "regressed" for x in cases), "unchanged": sum(x["outcome"] == "unchanged" for x in cases)}, "cases": cases}
    output_path.parent.mkdir(parents=True, exist_ok=True); output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"); return report


if __name__ == "__main__":
    result = run_ab(Path("outputs/local_rag/bm25_rewrite_ab.json")); print(json.dumps({"comparison": result["comparison"], "outcomes": result["outcomes"]}, ensure_ascii=False, indent=2))
