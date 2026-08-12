"""Stratified comparison of replaceable DOI authority providers."""

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
        report = json.loads(
            (snapshot_dir / "latest_retrieval_online.json").read_text(encoding="utf-8")
        )
        snapshot_id = report.get("snapshot_id", "legacy")
        for case in report["profiles"]["openalex"]["cases"]:
            for paper in case["ranked_papers"]:
                doi = normalize_doi(paper.get("doi"))
                if not doi or doi.startswith("10.48550/arxiv."):
                    continue
                row = by_doi.setdefault(
                    doi,
                    {
                        "doi": doi,
                        "doi_prefix": doi.split("/", 1)[0],
                        "claimed_title": paper.get("title", ""),
                        "claimed_year": paper.get("year"),
                        "snapshots": set(),
                        "case_ids": set(),
                    },
                )
                row["snapshots"].add(snapshot_id)
                row["case_ids"].add(case["case_id"])
    return [
        {
            **row,
            "snapshots": sorted(row["snapshots"]),
            "case_ids": sorted(row["case_ids"]),
        }
        for row in by_doi.values()
        if len(row["snapshots"]) == len(snapshot_dirs)
    ]


def select_stratified_claims(
    claims: list[dict[str, Any]], sample_size: int
) -> list[dict[str, Any]]:
    """Round-robin DOI prefixes so a dominant registrant cannot fill the sample."""

    groups: dict[str, list[dict[str, Any]]] = {}
    for claim in sorted(claims, key=lambda row: row["doi"]):
        groups.setdefault(claim["doi_prefix"], []).append(claim)
    selected: list[dict[str, Any]] = []
    depth = 0
    while len(selected) < min(sample_size, len(claims)):
        added = False
        for prefix in sorted(groups):
            if depth < len(groups[prefix]):
                selected.append(groups[prefix][depth])
                added = True
                if len(selected) == min(sample_size, len(claims)):
                    break
        if not added:
            break
        depth += 1
    return selected


class AuthorityFetcher:
    def __init__(self, provider: str, cache_dir: Path) -> None:
        _, self.router, self.executor = build_default_tool_runtime()
        self.provider = provider
        self.cache_dir = cache_dir / provider
        self.actual_api_call_count = 0
        self.cache_hit_count = 0

    def fetch(self, doi: str) -> dict[str, Any]:
        cache_path = self.cache_dir / f"{doi.replace('/', '__')}.json"
        if cache_path.exists():
            self.cache_hit_count += 1
            return json.loads(cache_path.read_text(encoding="utf-8"))
        self.actual_api_call_count += 1
        result = self.executor.execute(
            self.router.resolve("paper.lookup", self.provider), {"identity": doi}
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
            cache_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        return payload


class CrossrefAuthorityFetcher(AuthorityFetcher):
    """Backward-compatible Crossref-only fetcher used by existing callers."""

    def __init__(self, cache_dir: Path) -> None:
        super().__init__("crossref", cache_dir)


def evaluate_claims(
    claims: list[dict[str, Any]], fetcher: AuthorityFetcher
) -> dict[str, Any]:
    rows = []
    for claim in claims:
        result = fetcher.fetch(claim["doi"])
        paper = result.get("paper") or {}
        similarity = (
            title_similarity(claim["claimed_title"], paper.get("title", ""))
            if paper
            else 0.0
        )
        status = "FAILED"
        if result["success"] and paper:
            status = "MATCH" if similarity >= 0.7 else "TITLE_CONFLICT"
        elif result["success"]:
            status = "NOT_FOUND"
        rows.append(
            {
                **claim,
                "provider": getattr(fetcher, "provider", "crossref"),
                "status": status,
                "canonical_title": paper.get("title", ""),
                "canonical_year": paper.get("year"),
                "title_similarity": round(similarity, 6),
                "error_code": result.get("error_code", ""),
                "error_message": result.get("error_message", ""),
            }
        )
    successful = [row for row in rows if row["status"] != "FAILED"]
    return {
        "provider": getattr(fetcher, "provider", "crossref"),
        "claim_count": len(rows),
        "successful_lookup_count": len(successful),
        "coverage_rate": round(len(successful) / len(rows), 6) if rows else 1.0,
        "match_count": sum(row["status"] == "MATCH" for row in rows),
        "title_conflict_count": sum(
            row["status"] == "TITLE_CONFLICT" for row in rows
        ),
        "not_found_count": sum(row["status"] == "NOT_FOUND" for row in rows),
        "failed_count": sum(row["status"] == "FAILED" for row in rows),
        "actual_api_call_count": getattr(fetcher, "actual_api_call_count", 0),
        "cache_hit_count": getattr(fetcher, "cache_hit_count", 0),
        "rows": rows,
    }


def compare_providers(results: list[dict[str, Any]]) -> dict[str, Any]:
    by_provider = {
        result["provider"]: {row["doi"]: row for row in result["rows"]}
        for result in results
    }
    providers = list(by_provider)
    if len(providers) < 2:
        return {"comparable_count": 0, "title_agreement_count": 0, "title_agreement_rate": 0.0}
    left, right = providers[:2]
    comparable = []
    for doi in sorted(set(by_provider[left]) & set(by_provider[right])):
        a, b = by_provider[left][doi], by_provider[right][doi]
        if a["status"] in {"MATCH", "TITLE_CONFLICT"} and b["status"] in {"MATCH", "TITLE_CONFLICT"}:
            comparable.append(title_similarity(a["canonical_title"], b["canonical_title"]))
    agreements = sum(score >= 0.7 for score in comparable)
    return {
        "providers": providers[:2],
        "comparable_count": len(comparable),
        "title_agreement_count": agreements,
        "title_agreement_rate": round(agreements / len(comparable), 6) if comparable else 0.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare DOI authority providers.")
    parser.add_argument("snapshot_dirs", nargs="+", type=Path)
    parser.add_argument("--sample-size", type=int, default=40)
    parser.add_argument("--providers", default="crossref,semantic_scholar")
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    snapshot_dirs = [path.resolve() for path in args.snapshot_dirs]
    population = collect_stable_ordinary_doi_claims(snapshot_dirs)
    claims = select_stratified_claims(population, args.sample_size)
    providers = [item.strip() for item in args.providers.split(",") if item.strip()]
    results = [
        evaluate_claims(claims, AuthorityFetcher(provider, args.cache_dir.resolve()))
        for provider in providers
    ]
    report = {
        "report_version": "2.0",
        "sampling_method": "doi_prefix_round_robin",
        "snapshot_count": len(snapshot_dirs),
        "population_size": len(population),
        "sample_size": len(claims),
        "represented_prefix_count": len({row["doi_prefix"] for row in claims}),
        "provider_results": results,
        "provider_comparison": compare_providers(results),
        "rows": [row for result in results for row in result["rows"]],
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.output_dir / "latest_crossref_authority_eval.json"
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    for result in results:
        print(
            f"{result['provider']}: coverage={result['coverage_rate']:.4f} "
            f"matches={result['match_count']} conflicts={result['title_conflict_count']} "
            f"not_found={result['not_found_count']} failed={result['failed_count']}"
        )
    print(f"Report written to: {output_path}")


if __name__ == "__main__":
    main()
