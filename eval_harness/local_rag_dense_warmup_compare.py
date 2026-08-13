"""比较同一 Dense 模型在固定预热协议前后的稳定性。"""

from __future__ import annotations

import json
from pathlib import Path


def compare(before_path: Path, after_path: Path, output_path: Path) -> dict:
    before = json.loads(before_path.read_text(encoding="utf-8"))
    after = json.loads(after_path.read_text(encoding="utf-8"))
    metrics = {}
    for key in ("development_average_query_ms", "development_p95_query_ms", "holdout_average_query_ms", "holdout_p95_query_ms"):
        old, new = before["timing"][key], after["timing"][key]
        metrics[key] = {
            "before_mean_ms": old["mean"], "after_mean_ms": new["mean"],
            "mean_change_pct": round((new["mean"] / old["mean"] - 1) * 100, 2),
            "before_cv": old["cv"], "after_cv": new["cv"],
            "cv_change_pct_points": round((new["cv"] - old["cv"]) * 100, 2),
        }
    report = {
        "report_version": "1.0",
        "same_model": before.get("models") == after.get("models"),
        "quality_preserved": all(after[key] for key in ("quality_equal", "top5_rankings_equal", "scores_equal")),
        "warmup_protocol_match": after.get("warmup_protocol_match", False),
        "metrics": metrics,
        "decision": {
            "warmup_explains_instability": not before["decision"]["stability_validated"] and after["decision"]["stability_validated"],
            "stability_validated": after["decision"]["stability_validated"],
            "production_default": False,
            "next_step": "Dense + BM25 Hybrid 互补对照" if after["decision"]["stability_validated"] else "停止重复复测并诊断 ONNX/CPU 调度",
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(compare(Path("outputs/local_rag/mpnet_stability.json"), Path("outputs/local_rag/mpnet_warmup_stability.json"), Path("outputs/local_rag/mpnet_warmup_compare.json")), ensure_ascii=False, indent=2))
