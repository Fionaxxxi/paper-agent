"""对 Research Plan 的综合声明执行确定性证据覆盖检查。"""

from __future__ import annotations

from typing import Any


def evaluate_evidence_coverage(evidence_store: dict[str, Any]) -> dict[str, Any]:
    claims = list(evidence_store.get("claim_evidence_inputs", []))
    if not evidence_store.get("enabled"):
        return {
            "enabled": False, "status": "not_applicable", "claim_count": 0,
            "covered_claim_count": 0, "coverage_pct": 0.0,
            "uncovered_claims": [], "writer_allowed": True,
        }

    if not claims:
        return {
            "enabled": True, "status": "no_synthesis_claims", "claim_count": 0,
            "covered_claim_count": 0, "coverage_pct": 0.0,
            "uncovered_claims": [], "writer_allowed": bool(evidence_store.get("evidence")),
        }

    covered = [claim for claim in claims if claim.get("coverage_ready")]
    uncovered = [
        {
            "task_id": claim.get("task_id", ""),
            "claim": claim.get("claim", ""),
            "missing_dependency_task_ids": claim.get("missing_dependency_task_ids", []),
        }
        for claim in claims if not claim.get("coverage_ready")
    ]
    coverage_pct = round(len(covered) / len(claims) * 100, 2)
    if not covered:
        status = "blocked"
    elif uncovered:
        status = "partial"
    else:
        status = "passed"
    return {
        "enabled": True,
        "status": status,
        "claim_count": len(claims),
        "covered_claim_count": len(covered),
        "coverage_pct": coverage_pct,
        "uncovered_claims": uncovered,
        "writer_allowed": bool(covered),
    }
