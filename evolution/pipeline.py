from __future__ import annotations

import json
import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from evolution.candidate_generator import generate_candidates
from evolution.failure_dataset import build_failure_dataset
from evolution.models import Scorecard
from evolution.promotion_gate import evaluate_promotion
from evolution.registry import StrategyVersionRegistry


def run_evolution_cycle(
    *,
    failure_sources: list[Path],
    scorecards_path: Path,
    output_dir: Path,
    registry_path: Path,
) -> dict[str, Any]:
    scorecards = json.loads(scorecards_path.read_text(encoding="utf-8"))
    baseline = Scorecard.model_validate(scorecards["baseline"])
    candidate = Scorecard.model_validate(scorecards["candidate"])
    dataset = build_failure_dataset(failure_sources)
    candidates = generate_candidates(dataset)
    decision = evaluate_promotion(baseline, candidate)
    report = {
        "report_version": "1.0",
        "mode": "controlled_strategy_evolution",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "safety": {
            "auto_apply": False,
            "human_approval_required": True,
            "allowed_change_scope": ["prompt", "few_shot", "policy", "retrieval", "routing"],
            "forbidden_change_scope": ["source_code", "authentication", "tool_permission", "deployment"],
        },
        "failure_dataset": dataset.model_dump(mode="json"),
        "strategy_candidates": [item.model_dump(mode="json") for item in candidates],
        "baseline": baseline.model_dump(mode="json"),
        "candidate_scorecard": candidate.model_dump(mode="json"),
        "promotion_decision": decision.model_dump(mode="json"),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    latest = output_dir / "latest_evolution_report.json"
    latest.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    failures_csv = output_dir / "latest_evolution_failures.csv"
    with failures_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        fields = ["case_id", "trace_id", "module", "failure_type", "severity", "query", "source"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for record in dataset.records:
            writer.writerow({name: getattr(record, name) for name in fields})
    candidates_csv = output_dir / "latest_evolution_candidates.csv"
    with candidates_csv.open("w", encoding="utf-8-sig", newline="") as handle:
        fields = ["candidate_id", "target_module", "change_type", "risk_level", "case_count", "rationale", "requires_human_approval", "auto_apply"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in candidates:
            writer.writerow({
                "candidate_id": item.candidate_id,
                "target_module": item.target_module,
                "change_type": item.change_type,
                "risk_level": item.risk_level,
                "case_count": len(item.evidence_case_ids),
                "rationale": item.rationale,
                "requires_human_approval": item.requires_human_approval,
                "auto_apply": item.auto_apply,
            })
    report["artifacts"] = {
        "json": str(latest),
        "failure_csv": str(failures_csv),
        "candidate_csv": str(candidates_csv),
    }
    registry = StrategyVersionRegistry(registry_path)
    registry_record = {
        "version": candidate.version,
        "status": decision.status,
        "gate_passed": decision.gate_passed,
        "candidate_ids": [item.candidate_id for item in candidates],
        "report_path": str(latest),
        "rollback_version": baseline.version,
    }
    try:
        registry.register(registry_record)
        report["registry_status"] = "registered"
    except ValueError:
        report["registry_status"] = "already_registered"
    latest.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
