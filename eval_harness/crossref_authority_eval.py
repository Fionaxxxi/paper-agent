"""Evaluate Crossref as a replaceable authority provider for ordinary DOI claims."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from retrieval.metadata_resolver import normalize_doi, title_similarity
from tools.runtime import build_default_tool_runtime


def collect_stable_ordinary_doi_claims(snapshot_dirs: list[Path]) -> list[dict[str, Any]]:
    by_doi: dict[str, dict[str, Any]] = {}
    for snapshot_dir in snapshot_dirs:
        report = json.loads((snapshot_dir / "latest_retrieval_online.json").read_text(encoding="utf-8"))
        snapshot_id = report.get("snapshot_id", "legacy")
        for case in report["profiles"]["openalex"]["cases"]:
            for paper in case["ranked_papers"]:
                doi = normalize_doi(paper.get("doi"))
                if not doi or doi.startswith("10.48550/arxiv."):
                    continue
                row = by_doi.setdefault(doi, {"doi": doi, "claimed_title": paper.get("title", ""), "snapshots": set(), "case_ids": set()})
                row["snapshots"].add(snapshot_id)
                row["case_ids"].add(case["case_id"])
    return [
        {**row, "snapshots": sorted(row["snapshots"]), "case_ids": sorted(row["case_ids"])}
        for row in by_doi.values()
        if len(row["snapshots"]) == len(snapshot_dirs)
    ]


class CrossrefAuthorityFetcher:
    def __init__(self, cache_dir: Path) -> None:
        _, self.router, self.executor = build_default_tool_runtime()
        self.cache_dir = cache_dir
        self.actual_api_call_count = 0
        self.cache_hit_count = 0

    def fetch(self, doi: str) -> dict[str, Any]:
        safe_name = doi.replace("/", "__")
        cache_path = self.cache_dir / f"{safe_name}.json"
        if cache_path.exists():
            self.cache_hit_count += 1
            return json.loads(cache_path.read_text(encoding="utf-8"))
        self.actual_api_call_count += 1
        result = self.executor.execute(
            self.router.resolve("paper.lookup", "crossref"), {"identity": doi}
        )
        payload = {
            "doi": doi,
            "success": result.success,
            "error_code": result.error_code,
            "error_message": result.error_message,
            "paper": result.data.get("paper") if result.success else None,
        }
        if result.success:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return payload


def evaluate_claims(claims: list[dict[str, Any]], fetcher: CrossrefAuthorityFetcher) -> dict[str, Any]:
    rows = []
    for claim in claims:
        result = fetcher.fetch(claim["doi"])
        paper = result.get("paper") or {}
        similarity = title_similarity(claim["claimed_title"], paper.get("title", "")) if paper else 0.0
        status = "FAILED"
        if result["success"] and paper:
            status = "MATCH" if similarity >= 0.7 else "TITLE_CONFLICT"
        elif result["success"]:
            status = "NOT_FOUND"
        rows.append({**claim, "status": status, "canonical_title": paper.get("title", ""), "title_similarity": round(similarity, 6), "error_code": result.get("error_code", "")})
    successful = [row for row in rows if row["status"] != "FAILED"]
    return {
        "claim_count": len(rows),
        "successful_lookup_count": len(successful),
        "coverage_rate": round(len(successful) / len(rows), 6) if rows else 1.0,
        "match_count": sum(row["status"] == "MATCH" for row in rows),
        "title_conflict_count": sum(row["status"] == "TITLE_CONFLICT" for row in rows),
        "not_found_count": sum(row["status"] == "NOT_FOUND" for row in rows),
        "failed_count": sum(row["status"] == "FAILED" for row in rows),
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate Crossref DOI authority coverage.")
    parser.add_argument("snapshot_dirs", nargs="+", type=Path)
    parser.add_argument("--sample-size", type=int, default=20)
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    snapshot_dirs = [path.resolve() for path in args.snapshot_dirs]
    claims = sorted(collect_stable_ordinary_doi_claims(snapshot_dirs), key=lambda row: row["doi"])[: args.sample_size]
    fetcher = CrossrefAuthorityFetcher(args.cache_dir.resolve())
    evaluation = evaluate_claims(claims, fetcher)
    report = {"report_version": "1.0", "snapshot_count": len(snapshot_dirs), "sample_size": len(claims), "actual_api_call_count": fetcher.actual_api_call_count, "cache_hit_count": fetcher.cache_hit_count, **evaluation}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.output_dir / "latest_crossref_authority_eval.json"
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"claims={report['claim_count']} coverage={report['coverage_rate']:.4f} matches={report['match_count']} conflicts={report['title_conflict_count']} failed={report['failed_count']}")
    print(f"Report written to: {output_path}")


if __name__ == "__main__":
    main()
