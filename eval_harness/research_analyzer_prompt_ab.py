"""Research Analyzer zero-shot 与 few-shot 的轻量、显式在线 A/B。"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.config import settings
from research.analyzer import analyze_with_llm, build_analyzer_prompt


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "eval_harness/datasets/research_analyzer_prompt_ab_v1.json"
DEFAULT_OUTPUT = ROOT / "outputs/research_analyzer_prompt_ab"
PLACEHOLDER_KEYS = {"", "your_api_key_here", "sk-xxx", "test"}
VARIANTS = ("zero_shot", "few_shot")


def load_dataset(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    cases = data.get("cases", [])
    ids = [case.get("id") for case in cases]
    if not data.get("frozen") or len(cases) != 6 or len(ids) != len(set(ids)):
        raise ValueError("Analyzer A/B 数据集必须冻结并包含6个唯一案例")
    return data


def grade(case: dict[str, Any], analysis: Any) -> dict[str, Any]:
    objectives = " ".join(analysis.objectives)
    dimensions = " ".join(analysis.evaluation_dimensions)
    missing_objectives = [term for term in case["objective_terms"] if term not in objectives]
    dimension_hits = [term for term in case["dimension_any"] if term in dimensions]
    checks = {
        "task_level": analysis.task_level == case["expected_level"],
        "primary_skill": analysis.primary_skill == case["expected_skill"],
        "objective_coverage": not missing_objectives,
        "dimension_coverage": bool(dimension_hits),
        "multiple_sources": analysis.requires_multiple_sources is case["requires_multiple_sources"],
        "report_required": analysis.requires_report is True,
    }
    return {
        "passed": all(checks.values()), "checks": checks,
        "missing_objective_terms": missing_objectives,
        "dimension_hits": dimension_hits,
    }


def run_variant(cases: list[dict[str, Any]], variant: str) -> dict[str, Any]:
    rows = []
    for case in cases:
        try:
            analysis, usage = analyze_with_llm(case["query"], variant=variant)
            result = grade(case, analysis)
            rows.append({
                "id": case["id"], "variant": variant, "parsed": True,
                "passed": result["passed"], "checks": result["checks"],
                "missing_objective_terms": result["missing_objective_terms"],
                "dimension_hits": result["dimension_hits"],
                "actual_level": analysis.task_level, "actual_skill": analysis.primary_skill,
                "objectives": analysis.objectives, "dimensions": analysis.evaluation_dimensions,
                "requires_multiple_sources": analysis.requires_multiple_sources,
                "input_tokens": usage.get("input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
                "latency_seconds": usage.get("latency_seconds", 0),
                "prompt_version": usage.get("prompt_version", ""), "error": "",
            })
        except Exception as error:
            usage = getattr(error, "usage", {})
            rows.append({
                "id": case["id"], "variant": variant, "parsed": False,
                "passed": False, "checks": {}, "missing_objective_terms": case["objective_terms"],
                "dimension_hits": [], "actual_level": "", "actual_skill": "",
                "objectives": [], "dimensions": [], "requires_multiple_sources": False,
                "input_tokens": usage.get("input_tokens", 0), "output_tokens": usage.get("output_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0), "latency_seconds": usage.get("latency_seconds", 0),
                "prompt_version": usage.get("prompt_version", ""),
                "error": f"{type(error).__name__}: {error}",
            })
    count = len(rows)
    return {
        "variant": variant,
        "case_count": count,
        "parsed_count": sum(row["parsed"] for row in rows),
        "passed_count": sum(row["passed"] for row in rows),
        "pass_rate_pct": round(sum(row["passed"] for row in rows) / count * 100, 2),
        "parse_rate_pct": round(sum(row["parsed"] for row in rows) / count * 100, 2),
        "token_usage": sum(row["total_tokens"] for row in rows),
        "average_latency_seconds": round(sum(row["latency_seconds"] for row in rows) / count, 3),
        "rows": rows,
    }


def compare(zero: dict[str, Any], few: dict[str, Any]) -> dict[str, Any]:
    zero_tokens = zero["token_usage"]
    token_delta_pct = round((few["token_usage"] - zero_tokens) / zero_tokens * 100, 2) if zero_tokens else 0.0
    pass_delta = round(few["pass_rate_pct"] - zero["pass_rate_pct"], 2)
    promote = (
        few["parse_rate_pct"] >= zero["parse_rate_pct"]
        and few["pass_rate_pct"] >= 80.0
        and pass_delta >= 10.0
        and token_delta_pct <= 250.0
    )
    return {
        "pass_rate_delta_pct_points": pass_delta,
        "token_delta_pct": token_delta_pct,
        "latency_delta_seconds": round(few["average_latency_seconds"] - zero["average_latency_seconds"], 3),
        "promote_few_shot": promote,
        "decision": "promote" if promote else "keep_zero_shot",
    }


def offline_contract(dataset: dict[str, Any]) -> dict[str, Any]:
    lengths = {variant: len(build_analyzer_prompt("测试请求", variant)) for variant in VARIANTS}
    return {
        "mode": "offline_contract", "dataset_version": dataset["version"],
        "summary": {"case_count": len(dataset["cases"]), "llm_call_count": 0,
                    "zero_shot_prompt_chars": lengths["zero_shot"],
                    "few_shot_prompt_chars": lengths["few_shot"]},
        "variants": [], "comparison": {},
    }


def run_online(dataset: dict[str, Any]) -> dict[str, Any]:
    results = {variant: run_variant(dataset["cases"], variant) for variant in VARIANTS}
    return {
        "mode": "online_ab", "dataset_version": dataset["version"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "summary": {"case_count": len(dataset["cases"]), "llm_call_count": 12,
                    "token_usage": sum(result["token_usage"] for result in results.values())},
        "variants": [results[variant] for variant in VARIANTS],
        "comparison": compare(results["zero_shot"], results["few_shot"]),
    }


def write_report(report: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = "online" if report["mode"] == "online_ab" else "offline"
    json_path = output_dir / f"latest_analyzer_prompt_ab_{suffix}.json"
    csv_path = output_dir / f"latest_analyzer_prompt_ab_{suffix}.csv"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    rows = []
    for variant in report.get("variants", []):
        for row in variant["rows"]:
            rows.append({**row, "checks": json.dumps(row["checks"], ensure_ascii=False),
                         "missing_objective_terms": " | ".join(row["missing_objective_terms"]),
                         "dimension_hits": " | ".join(row["dimension_hits"]),
                         "objectives": " | ".join(row["objectives"]),
                         "dimensions": " | ".join(row["dimensions"])})
    if rows:
        with csv_path.open("w", encoding="utf-8-sig", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    else:
        summary_row = {"mode": report["mode"], **report["summary"]}
        with csv_path.open("w", encoding="utf-8-sig", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=list(summary_row))
            writer.writeheader(); writer.writerow(summary_row)
    return json_path, csv_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--confirm-online", action="store_true")
    args = parser.parse_args()
    dataset = load_dataset(args.dataset.resolve())
    if args.confirm_online:
        if settings.OPENAI_API_KEY.strip().casefold() in PLACEHOLDER_KEYS:
            raise ValueError("在线 A/B 需要有效 OPENAI_API_KEY")
        report = run_online(dataset)
    else:
        report = offline_contract(dataset)
    json_path, csv_path = write_report(report, args.output_dir.resolve())
    print(json.dumps({"summary": report["summary"], "comparison": report["comparison"]}, ensure_ascii=False, indent=2))
    print(f"JSON: {json_path}"); print(f"CSV: {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
