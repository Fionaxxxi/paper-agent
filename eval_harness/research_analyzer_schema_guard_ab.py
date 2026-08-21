from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from core.config import settings
from eval_harness.research_analyzer_prompt_ab import (
    DEFAULT_DATASET,
    DEFAULT_OUTPUT,
    PLACEHOLDER_KEYS,
    load_dataset,
    run_variant,
    write_report,
)


def run_online(dataset: dict) -> dict:
    baseline = run_variant(dataset["cases"], "zero_shot")
    candidate = run_variant(dataset["cases"], "schema_guard")
    zero_tokens = baseline["token_usage"]
    return {
        "mode": "online_ab",
        "experiment": "zero_shot_vs_schema_guard",
        "dataset_version": dataset["version"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "case_count": len(dataset["cases"]), "llm_call_count": 12,
            "token_usage": baseline["token_usage"] + candidate["token_usage"],
        },
        "variants": [baseline, candidate],
        "comparison": {
            "pass_rate_delta_pct_points": round(candidate["pass_rate_pct"] - baseline["pass_rate_pct"], 2),
            "token_delta_pct": round((candidate["token_usage"] - zero_tokens) / zero_tokens * 100, 2) if zero_tokens else 0.0,
            "latency_delta_seconds": round(candidate["average_latency_seconds"] - baseline["average_latency_seconds"], 3),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="真实测试 Research Analyzer 最小 Schema Guard 候选")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT / "schema_guard")
    parser.add_argument("--confirm-online", action="store_true")
    args = parser.parse_args()
    if not args.confirm_online:
        raise ValueError("Schema Guard A/B 只生成真实在线结果，必须传 --confirm-online")
    if settings.OPENAI_API_KEY.strip().casefold() in PLACEHOLDER_KEYS:
        raise ValueError("在线 A/B 需要有效 OPENAI_API_KEY")
    report = run_online(load_dataset(args.dataset.resolve()))
    json_path, csv_path = write_report(report, args.output_dir.resolve())
    print(json.dumps({"summary": report["summary"], "comparison": report["comparison"]}, ensure_ascii=False, indent=2))
    print(f"JSON: {json_path}")
    print(f"CSV: {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
