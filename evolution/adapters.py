from __future__ import annotations

import math
from typing import Any

from evolution.models import Scorecard


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return round(ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)], 4)


def analyzer_ab_scorecards(report: dict[str, Any]) -> tuple[Scorecard, Scorecard]:
    variants = {item["variant"]: item for item in report.get("variants", [])}
    if set(variants) != {"zero_shot", "few_shot"}:
        raise ValueError("analyzer A/B report must contain zero_shot and few_shot")

    def convert(name: str, version: str) -> Scorecard:
        variant = variants[name]
        rows = variant["rows"]
        provider_failures = sum(
            any(marker in str(row.get("error", "")) for marker in ("APIConnectionError", "Timeout", "RateLimit"))
            for row in rows
        )
        return Scorecard(
            version=version,
            case_ids=[str(row["id"]) for row in rows],
            pass_rate_pct=float(variant["pass_rate_pct"]),
            critical_pass_rate_pct=100.0,
            safety_pass_rate_pct=100.0,
            provider_failure_count=provider_failures,
            average_tokens=round(float(variant["token_usage"]) / max(1, len(rows)), 4),
            p95_latency_seconds=_p95([float(row.get("latency_seconds", 0)) for row in rows]),
            per_case_passed={str(row["id"]): bool(row["passed"]) for row in rows},
        )

    dataset_version = report.get("dataset_version", "unknown")
    return (
        convert("zero_shot", f"research-analyzer-zero-shot-{dataset_version}"),
        convert("few_shot", f"research-analyzer-few-shot-{dataset_version}"),
    )


def analyzer_baseline_failures(report: dict[str, Any]) -> dict[str, Any]:
    zero = next(item for item in report.get("variants", []) if item.get("variant") == "zero_shot")
    cases = []
    for row in zero["rows"]:
        if row.get("passed"):
            continue
        failures = [name for name, passed in row.get("checks", {}).items() if not passed]
        if not row.get("parsed", True):
            failures.append("research_analyzer_parse_error")
        cases.append({
            "case_id": row["id"],
            "module": "research_analyzer",
            "query": "",
            "passed": False,
            "failure_types": list(dict.fromkeys(failures)),
            "checks": row.get("checks", {}),
            "actual": {"level": row.get("actual_level"), "skill": row.get("actual_skill")},
        })
    return {"dataset_version": report.get("dataset_version"), "cases": cases}
