"""比较 Dense 冷/热启动，验证缓存只优化成本而不改变质量。"""

from __future__ import annotations

import json
from pathlib import Path


QUALITY_KEYS = ("recall_at_1", "recall_at_3", "recall_at_5", "mrr_at_5", "ndcg_at_5", "page_recall_at_5", "page_ndcg_at_5")


def compare(cold_path: Path, warm_path: Path, output_path: Path) -> dict:
    cold = json.loads(cold_path.read_text(encoding="utf-8")); warm = json.loads(warm_path.read_text(encoding="utf-8"))
    quality_equal = all(cold[split]["summary"][key] == warm[split]["summary"][key] for split in ("development", "holdout") for key in QUALITY_KEYS)
    build_cold, build_warm = cold["timing"]["index_build_ms"], warm["timing"]["index_build_ms"]
    report = {
        "report_version": "1.0",
        "cache": {"cold_hit": cold["cache"]["hit"], "warm_hit": warm["cache"]["hit"], "fingerprint_equal": cold["cache"]["fingerprint"] == warm["cache"]["fingerprint"]},
        "quality_equal": quality_equal,
        "timing": {"cold_index_build_ms": build_cold, "warm_cache_load_ms": warm["timing"]["cache_load_ms"], "warm_index_build_ms": build_warm, "index_build_reduction_pct": round((1 - build_warm / build_cold) * 100, 4)},
        "decision": {"cache_validated": not cold["cache"]["hit"] and warm["cache"]["hit"] and quality_equal and build_warm < build_cold * 0.01, "production_default": False, "next_step": "重复运行稳定性评测"},
    }
    output_path.parent.mkdir(parents=True, exist_ok=True); output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(compare(Path("outputs/local_rag/dense_cache_cold.json"), Path("outputs/local_rag/dense_multilingual_minilm.json"), Path("outputs/local_rag/dense_cache_compare.json")), ensure_ascii=False, indent=2))
