"""Compare independent retrieval snapshots without hiding per-case changes."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


QUALITY_METRICS = ("recall_at_5", "mrr_at_5", "ndcg_at_5")


def load_report(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _snapshot_complete(report: dict[str, Any]) -> bool:
    return all(
        payload["summary"].get("failed_count", 0) == 0
        and payload["summary"].get("partial_success_count", 0) == 0
        for payload in report["profiles"].values()
    )


def _quarantine_records(report: dict[str, Any], profile: str) -> list[dict[str, Any]]:
    records = []
    for case in report["profiles"][profile]["cases"]:
        for paper in case.get("quarantined_documents", []):
            records.append(
                {
                    "case_id": case["case_id"],
                    "query": case["query"],
                    "canonical_identity": paper.get("canonical_identity", ""),
                    "title": paper.get("title", ""),
                    "source": paper.get("source", ""),
                    "warnings": paper.get("metadata_warnings", []),
                }
            )
    return records


def _quarantine_key(record: dict[str, Any]) -> tuple[str, str, str]:
    return (
        record["case_id"],
        record["canonical_identity"],
        record["title"],
    )


def compare_snapshots(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    *,
    target_profile: str = "multi_verified_rerank",
    quarantine_stability_threshold: float = 0.8,
) -> dict[str, Any]:
    """Return profile, case and quarantine deltas plus a promotion gate."""

    common_profiles = sorted(set(baseline["profiles"]) & set(candidate["profiles"]))
    if target_profile not in common_profiles:
        raise ValueError(f"target profile missing from one snapshot: {target_profile}")

    profile_deltas = []
    for profile in common_profiles:
        first = baseline["profiles"][profile]["summary"]
        second = candidate["profiles"][profile]["summary"]
        row = {"profile": profile}
        for metric in QUALITY_METRICS:
            key = f"mean_{metric}"
            row[f"baseline_{metric}"] = first.get(key, 0.0)
            row[f"candidate_{metric}"] = second.get(key, 0.0)
            row[f"delta_{metric}"] = round(second.get(key, 0.0) - first.get(key, 0.0), 6)
        profile_deltas.append(row)

    baseline_cases = {
        case["case_id"]: case
        for case in baseline["profiles"][target_profile]["cases"]
    }
    candidate_cases = {
        case["case_id"]: case
        for case in candidate["profiles"][target_profile]["cases"]
    }
    case_deltas = []
    critical_regressions = []
    for case_id in sorted(set(baseline_cases) & set(candidate_cases)):
        first = baseline_cases[case_id]
        second = candidate_cases[case_id]
        row = {"case_id": case_id, "query": second["query"]}
        regressed_metrics = []
        for metric in QUALITY_METRICS:
            delta = round(second.get(metric, 0.0) - first.get(metric, 0.0), 6)
            row[f"baseline_{metric}"] = first.get(metric, 0.0)
            row[f"candidate_{metric}"] = second.get(metric, 0.0)
            row[f"delta_{metric}"] = delta
            if delta < 0:
                regressed_metrics.append(metric)
        row["regressed_metrics"] = regressed_metrics
        case_deltas.append(row)
        if regressed_metrics:
            critical_regressions.append(row)

    first_quarantine = _quarantine_records(baseline, target_profile)
    second_quarantine = _quarantine_records(candidate, target_profile)
    first_by_key = {_quarantine_key(record): record for record in first_quarantine}
    second_by_key = {_quarantine_key(record): record for record in second_quarantine}
    first_keys = set(first_by_key)
    second_keys = set(second_by_key)
    union = first_keys | second_keys
    overlap = first_keys & second_keys
    stability = len(overlap) / len(union) if union else 1.0
    quarantine_changes = [
        {"change": "stable", **second_by_key[key]} for key in sorted(overlap)
    ] + [
        {"change": "removed", **first_by_key[key]} for key in sorted(first_keys - second_keys)
    ] + [
        {"change": "added", **second_by_key[key]} for key in sorted(second_keys - first_keys)
    ]

    target_delta = next(row for row in profile_deltas if row["profile"] == target_profile)
    summary_regressions = [
        metric for metric in QUALITY_METRICS if target_delta[f"delta_{metric}"] < 0
    ]
    blockers = []
    if not _snapshot_complete(baseline) or not _snapshot_complete(candidate):
        blockers.append("INCOMPLETE_SNAPSHOT")
    if summary_regressions or critical_regressions:
        blockers.append("QUALITY_REGRESSION")
    if stability < quarantine_stability_threshold:
        blockers.append("QUARANTINE_INSTABILITY")

    return {
        "report_version": "1.0",
        "baseline_snapshot_id": baseline.get("snapshot_id", "legacy"),
        "candidate_snapshot_id": candidate.get("snapshot_id", "legacy"),
        "dataset_version": candidate["dataset_version"],
        "target_profile": target_profile,
        "baseline_complete": _snapshot_complete(baseline),
        "candidate_complete": _snapshot_complete(candidate),
        "profile_deltas": profile_deltas,
        "case_deltas": case_deltas,
        "critical_regression_count": len(critical_regressions),
        "critical_regressions": critical_regressions,
        "quarantine": {
            "baseline_count": len(first_keys),
            "candidate_count": len(second_keys),
            "stable_count": len(overlap),
            "added_count": len(second_keys - first_keys),
            "removed_count": len(first_keys - second_keys),
            "jaccard_stability": round(stability, 6),
            "required_stability": quarantine_stability_threshold,
            "changes": quarantine_changes,
        },
        "promotion_ready": not blockers,
        "promotion_blockers": blockers,
    }


def write_comparison(comparison: dict[str, Any], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "latest_snapshot_comparison.json"
    json_path.write_text(
        json.dumps(comparison, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tables = {
        "snapshot_profile_deltas.csv": comparison["profile_deltas"],
        "snapshot_case_deltas.csv": comparison["case_deltas"],
        "snapshot_quarantine_changes.csv": comparison["quarantine"]["changes"],
    }
    for filename, rows in tables.items():
        if not rows:
            continue
        with (output_dir / filename).open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    return json_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare two retrieval snapshots.")
    parser.add_argument("baseline", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--target-profile", default="multi_verified_rerank")
    args = parser.parse_args()
    comparison = compare_snapshots(
        load_report(args.baseline.resolve()),
        load_report(args.candidate.resolve()),
        target_profile=args.target_profile,
    )
    output_path = write_comparison(comparison, args.output_dir.resolve())
    print(
        f"promotion_ready={comparison['promotion_ready']} "
        f"regressions={comparison['critical_regression_count']} "
        f"quarantine_stability={comparison['quarantine']['jaccard_stability']:.4f}"
    )
    print(f"Comparison written to: {output_path}")


if __name__ == "__main__":
    main()
