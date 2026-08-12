"""Small deterministic DOI contamination challenge used as a stop condition."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from retrieval.metadata_resolver import attach_authoritative_evidence, resolve_document_metadata


CASES = [
    {"id": "clean", "title": "Canonical Retrieval Study", "canonical": "Canonical Retrieval Study", "expected_repair": False},
    {"id": "corrupt_title", "title": "Unrelated Robotics Dataset", "canonical": "Canonical Retrieval Study", "expected_repair": True},
    {"id": "missing_title", "title": "", "canonical": "Canonical Retrieval Study", "expected_repair": True},
    {"id": "near_title", "title": "Canonical Retrieval Study Extended", "canonical": "Canonical Retrieval Study", "expected_repair": False},
    {"id": "not_found", "title": "Plausible DOI Work", "not_found": True, "expected_repair": False},
    {"id": "tool_failure", "title": "Plausible DOI Work", "tool_failure": True, "expected_repair": False},
]


def run_challenge() -> dict[str, Any]:
    rows = []
    for index, case in enumerate(CASES, start=1):
        doi = f"10.9999/challenge-{index}"
        document = {"title": case["title"], "doi": doi, "source": "openalex", "metadata_evidence": [{"title": case["title"], "doi": doi, "source": "openalex"}]}
        authority = {}
        if case.get("not_found"):
            authority[f"doi:{doi}"] = {"source": "crossref", "canonical_lookup_status": "NOT_FOUND"}
        elif not case.get("tool_failure"):
            authority[f"doi:{doi}"] = {"title": case["canonical"], "doi": doi, "source": "crossref"}
        resolved = resolve_document_metadata("retrieval study", attach_authoritative_evidence(document, authority))
        repaired = bool(resolved["metadata_repairs"])
        rows.append({
            **case,
            "doi": doi,
            "actual_title": resolved["title"],
            "repaired": repaired,
            "quarantined": resolved["metadata_quarantined"],
            "status": resolved["metadata_resolution_status"],
            "passed": repaired == case["expected_repair"] and not resolved["metadata_quarantined"],
        })
    expected_repairs = [row for row in rows if row["expected_repair"]]
    safe_cases = [row for row in rows if not row["expected_repair"]]
    return {
        "case_count": len(rows),
        "passed_count": sum(row["passed"] for row in rows),
        "repair_accuracy": round(sum(row["repaired"] for row in expected_repairs) / len(expected_repairs), 6),
        "false_repair_count": sum(row["repaired"] for row in safe_cases),
        "false_quarantine_count": sum(row["quarantined"] for row in rows),
        "acceptance_passed": all(row["passed"] for row in rows),
        "rows": rows,
    }


def write_report(path: Path) -> dict[str, Any]:
    report = run_challenge()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    report = write_report(Path("eval_harness/reports/doi_contamination_challenge.json"))
    print(f"passed={report['passed_count']}/{report['case_count']} acceptance={report['acceptance_passed']}")
