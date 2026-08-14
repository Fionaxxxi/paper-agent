"""复用在线Writer原文评测零LLM引用补全的前后差异。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from eval_harness.research_report_eval import grade_report, load_dataset
from research.citation_repair import repair_uncited_synthesis
from validators.research_citation_validator import validate_research_citations


def run_ab(dataset: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    cases = {case["id"]: case for case in dataset["cases"]}
    rows = []
    for prior in report["cases"]:
        case = cases[prior["id"]]
        state = {
            "task_level": "L3", "answer": prior["answer"],
            "research_coverage": {"enabled": True},
            "research_analysis": {"primary_skill": case["skill"]},
            "evidence_store": {"evidence": case["evidence"]},
        }
        before_validation = validate_research_citations(state).model_dump(mode="python")
        repair = repair_uncited_synthesis({**state, "citation_validation": before_validation})
        after_answer = repair["answer"]
        after_validation = validate_research_citations({**state, "answer": after_answer}).model_dump(mode="python")
        before_grade, after_grade = grade_report(case, prior["answer"]), grade_report(case, after_answer)
        rows.append({
            "id": prior["id"], "repair_status": repair["status"],
            "repaired_line_count": repair["repaired_line_count"],
            "added_evidence_ids": repair["added_evidence_ids"],
            "before_passed": before_grade["passed"], "after_passed": after_grade["passed"],
            "before_validator_passed": before_validation["passed"],
            "after_validator_passed": after_validation["passed"],
            "before_claim_coverage_pct": before_grade["metrics"]["claim_coverage_pct"],
            "after_claim_coverage_pct": after_grade["metrics"]["claim_coverage_pct"],
            "token_usage_delta": 0,
        })
    return {
        "evaluation": "citation_repair_zero_llm_ab",
        "source_report": report.get("mode", "unknown"),
        "summary": {
            "case_count": len(rows),
            "before_passed_count": sum(row["before_passed"] for row in rows),
            "after_passed_count": sum(row["after_passed"] for row in rows),
            "before_validator_passed_count": sum(row["before_validator_passed"] for row in rows),
            "after_validator_passed_count": sum(row["after_validator_passed"] for row in rows),
            "repaired_case_count": sum(row["repair_status"] == "repaired" for row in rows),
            "token_usage_delta": 0,
        }, "cases": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=Path("eval_harness/datasets/research_report_v1.json"))
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("outputs/research_report_eval_v2/citation_repair_ab.json"))
    args = parser.parse_args()
    result = run_ab(load_dataset(args.dataset), json.loads(args.report.read_text(encoding="utf-8")))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    print(f"JSON: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
