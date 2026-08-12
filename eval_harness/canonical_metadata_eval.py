"""Replay retrieval snapshots with canonical arXiv identity evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from eval_harness.retrieval_eval_models import load_retrieval_dataset
from eval_harness.retrieval_online import evaluate_case_profile, summarize_profile
from retrieval.metadata_resolver import extract_arxiv_ids, normalize_doi
from tools.runtime import build_default_tool_runtime


def load_provider_results(
    snapshot_dir: Path,
    dataset_version: str,
    case_id: str,
) -> dict[str, dict[str, Any]]:
    results = {}
    for provider in ("arxiv", "openalex"):
        path = snapshot_dir / "provider_cache" / dataset_version / provider / f"{case_id}.json"
        results[provider] = json.loads(path.read_text(encoding="utf-8"))
    return results


def collect_claimed_arxiv_ids(
    snapshot_dirs: list[Path],
    dataset_version: str,
    case_ids: list[str],
) -> list[str]:
    identities = set()
    for snapshot_dir in snapshot_dirs:
        for case_id in case_ids:
            results = load_provider_results(snapshot_dir, dataset_version, case_id)
            for paper in results["openalex"].get("papers", []):
                identities.update(extract_arxiv_ids(paper))
    return sorted(identities)


def collect_claimed_ordinary_dois(
    snapshot_dirs: list[Path],
    dataset_version: str,
    case_ids: list[str],
) -> list[str]:
    identities = set()
    for snapshot_dir in snapshot_dirs:
        for case_id in case_ids:
            results = load_provider_results(snapshot_dir, dataset_version, case_id)
            for paper in results["openalex"].get("papers", []):
                doi = normalize_doi(paper.get("doi"))
                if doi and not doi.startswith("10.48550/arxiv."):
                    identities.add(doi)
    return sorted(identities)


def collect_quarantined_arxiv_ids(snapshot_dirs: list[Path]) -> list[str]:
    """Limit the candidate experiment to identities changed by the v2 gate."""

    identities = set()
    for snapshot_dir in snapshot_dirs:
        report_path = snapshot_dir / "latest_retrieval_online.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        cases = report["profiles"]["multi_verified_rerank"]["cases"]
        for case in cases:
            for paper in case.get("quarantined_documents", []):
                identities.update(extract_arxiv_ids(paper))
    return sorted(identities)


class CanonicalArxivFetcher:
    def __init__(self, cache_dir: Path) -> None:
        _, self.router, self.executor = build_default_tool_runtime()
        self.cache_dir = cache_dir
        self.actual_api_call_count = 0
        self.cache_hit_count = 0
        self.not_found_count = 0

    @staticmethod
    def _authority_value(arxiv_id: str, paper: dict[str, Any] | None) -> dict[str, Any]:
        if paper is not None:
            return paper
        return {
            "source": "arxiv_authority",
            "canonical_identity": f"arxiv:{arxiv_id}",
            "canonical_lookup_status": "NOT_FOUND",
        }

    def fetch(self, arxiv_id: str) -> dict[str, Any] | None:
        cache_path = self.cache_dir / f"{arxiv_id}.json"
        if cache_path.exists():
            payload = json.loads(cache_path.read_text(encoding="utf-8"))
            if payload.get("success"):
                self.cache_hit_count += 1
                if payload.get("paper") is None:
                    self.not_found_count += 1
                return self._authority_value(arxiv_id, payload.get("paper"))

        self.actual_api_call_count += 1
        result = self.executor.execute(
            self.router.resolve("paper.lookup", "arxiv"),
            {"identity": arxiv_id},
        )
        payload = {
            "identity": arxiv_id,
            "success": result.success,
            "error_code": result.error_code,
            "error_message": result.error_message,
            "paper": result.data.get("paper") if result.success else None,
        }
        if payload["success"]:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        if not payload["success"]:
            return None
        if payload["paper"] is None:
            self.not_found_count += 1
        return self._authority_value(arxiv_id, payload["paper"])


class CanonicalDoiFetcher:
    def __init__(self, cache_dir: Path) -> None:
        _, self.router, self.executor = build_default_tool_runtime()
        self.cache_dir = cache_dir
        self.actual_api_call_count = 0
        self.cache_hit_count = 0
        self.not_found_count = 0
        self.failed_count = 0

    @staticmethod
    def _authority_value(doi: str, paper: dict[str, Any] | None) -> dict[str, Any]:
        if paper is not None:
            return paper
        return {
            "source": "crossref",
            "canonical_identity": f"doi:{doi}",
            "canonical_lookup_status": "NOT_FOUND",
        }

    def fetch(self, doi: str) -> dict[str, Any] | None:
        cache_path = self.cache_dir / f"{doi.replace('/', '__')}.json"
        if cache_path.exists():
            payload = json.loads(cache_path.read_text(encoding="utf-8"))
            if payload.get("success", True):
                self.cache_hit_count += 1
                paper = payload.get("paper", payload)
                if paper is None or paper.get("canonical_lookup_status") == "NOT_FOUND":
                    self.not_found_count += 1
                    paper = None
                return self._authority_value(doi, paper)

        self.actual_api_call_count += 1
        result = self.executor.execute(
            self.router.resolve("paper.lookup", "crossref"),
            {"identity": doi},
        )
        payload = {
            "identity": doi,
            "success": result.success,
            "error_code": result.error_code,
            "error_message": result.error_message,
            "paper": result.data.get("paper") if result.success else None,
        }
        if not payload["success"]:
            self.failed_count += 1
            return None
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        if payload["paper"] is None:
            self.not_found_count += 1
        return self._authority_value(doi, payload["paper"])


def build_authority_index(
    arxiv_ids: list[str],
    fetcher: CanonicalArxivFetcher,
) -> dict[str, dict[str, Any]]:
    authority = {}
    for arxiv_id in arxiv_ids:
        paper = fetcher.fetch(arxiv_id)
        if paper is not None:
            authority[f"arxiv:{arxiv_id}"] = paper
    return authority


def build_doi_authority_index(
    dois: list[str],
    fetcher: CanonicalDoiFetcher,
) -> dict[str, dict[str, Any]]:
    authority = {}
    for doi in dois:
        paper = fetcher.fetch(doi)
        if paper is not None:
            authority[f"doi:{doi}"] = paper
    return authority


def replay_snapshot(
    snapshot_dir: Path,
    dataset_path: Path,
    authority_by_identity: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    dataset = load_retrieval_dataset(dataset_path)
    cases = []
    for case in dataset.cases:
        provider_results = load_provider_results(
            snapshot_dir, dataset.dataset_version, case.id
        )
        cases.append(
            evaluate_case_profile(
                case,
                "multi_canonical_rerank",
                provider_results,
                dataset.k_values,
                authority_by_identity,
            )
        )
    return {
        "snapshot_id": snapshot_dir.name if snapshot_dir.name != "retrieval_online" else "legacy",
        "dataset_name": dataset.dataset_name,
        "dataset_version": dataset.dataset_version,
        "dataset_case_count": len(dataset.cases),
        "authority_identity_count": len(authority_by_identity),
        "profile": "multi_canonical_rerank",
        "summary": summarize_profile(
            "multi_canonical_rerank", cases, dataset.k_values
        ),
        "cases": cases,
    }


def evaluate_promotion(
    snapshot_dirs: list[Path],
    candidate_reports: list[dict[str, Any]],
    *,
    authority_identity_count: int,
    claimed_identity_count: int,
    minimum_snapshot_count: int = 3,
) -> dict[str, Any]:
    """Apply auditable v3 promotion gates across independent snapshots."""

    blockers = []
    comparisons = []
    total_regressions = 0
    for snapshot_dir, candidate in zip(snapshot_dirs, candidate_reports):
        baseline_report = json.loads(
            (snapshot_dir / "latest_retrieval_online.json").read_text(encoding="utf-8")
        )
        baseline = baseline_report["profiles"]["multi_verified_rerank"]
        baseline_cases = {case["case_id"]: case for case in baseline["cases"]}
        regressions = []
        for case in candidate["cases"]:
            first = baseline_cases[case["case_id"]]
            metrics = [
                name for name in ("recall_at_5", "mrr_at_5", "ndcg_at_5")
                if case[name] < first[name]
            ]
            if metrics:
                regressions.append({"case_id": case["case_id"], "metrics": metrics})
        total_regressions += len(regressions)
        comparisons.append(
            {
                "snapshot_id": candidate["snapshot_id"],
                "baseline_complete": all(
                    payload["summary"].get("failed_count", 0) == 0
                    and payload["summary"].get("partial_success_count", 0) == 0
                    for payload in baseline_report["profiles"].values()
                ),
                "quality_regression_count": len(regressions),
                "quality_regressions": regressions,
                "baseline_summary": baseline["summary"],
                "candidate_summary": candidate["summary"],
            }
        )
    coverage = authority_identity_count / claimed_identity_count if claimed_identity_count else 1.0
    if len(snapshot_dirs) < minimum_snapshot_count:
        blockers.append("INSUFFICIENT_SNAPSHOTS")
    if any(not row["baseline_complete"] for row in comparisons):
        blockers.append("INCOMPLETE_SNAPSHOT")
    if total_regressions:
        blockers.append("QUALITY_REGRESSION")
    if coverage < 1.0:
        blockers.append("INCOMPLETE_AUTHORITY_COVERAGE")
    return {
        "promotion_ready": not blockers,
        "promotion_blockers": blockers,
        "required_snapshot_count": minimum_snapshot_count,
        "actual_snapshot_count": len(snapshot_dirs),
        "authority_coverage": round(coverage, 6),
        "quality_regression_count": total_regressions,
        "comparisons": comparisons,
    }


def compare_candidate_reports(
    baseline_reports: list[dict[str, Any]],
    candidate_reports: list[dict[str, Any]],
) -> dict[str, Any]:
    """Measure the isolated DOI-authority delta over the arXiv-only canonical baseline."""

    comparisons = []
    regression_count = 0
    changed_ranked_case_count = 0
    for baseline, candidate in zip(baseline_reports, candidate_reports):
        baseline_cases = {case["case_id"]: case for case in baseline["cases"]}
        changed_cases = []
        regressions = []
        for case in candidate["cases"]:
            previous = baseline_cases[case["case_id"]]
            before = [paper["canonical_identity"] for paper in previous["ranked_papers"]]
            after = [paper["canonical_identity"] for paper in case["ranked_papers"]]
            if before != after:
                changed_cases.append(case["case_id"])
            if any(case[name] < previous[name] for name in ("recall_at_5", "mrr_at_5", "ndcg_at_5")):
                regressions.append(case["case_id"])
        regression_count += len(regressions)
        changed_ranked_case_count += len(changed_cases)
        comparisons.append({
            "snapshot_id": candidate["snapshot_id"],
            "delta_recall_at_5": round(candidate["summary"]["mean_recall_at_5"] - baseline["summary"]["mean_recall_at_5"], 6),
            "delta_mrr_at_5": round(candidate["summary"]["mean_mrr_at_5"] - baseline["summary"]["mean_mrr_at_5"], 6),
            "delta_ndcg_at_5": round(candidate["summary"]["mean_ndcg_at_5"] - baseline["summary"]["mean_ndcg_at_5"], 6),
            "changed_ranked_case_count": len(changed_cases),
            "changed_ranked_cases": changed_cases,
            "quality_regression_count": len(regressions),
            "quality_regressions": regressions,
        })
    return {
        "baseline": "arxiv_canonical_only",
        "candidate": "arxiv_plus_crossref_canonical",
        "quality_regression_count": regression_count,
        "changed_ranked_case_count": changed_ranked_case_count,
        "quality_improvement_claimed": any(
            row[metric] > 0
            for row in comparisons
            for metric in ("delta_recall_at_5", "delta_mrr_at_5", "delta_ndcg_at_5")
        ),
        "comparisons": comparisons,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay snapshots with canonical metadata.")
    parser.add_argument("snapshot_dirs", nargs="+", type=Path)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    dataset = load_retrieval_dataset(args.dataset.resolve())
    snapshot_dirs = [path.resolve() for path in args.snapshot_dirs]
    identities = collect_quarantined_arxiv_ids(snapshot_dirs)
    ordinary_dois = collect_claimed_ordinary_dois(
        snapshot_dirs,
        dataset.dataset_version,
        [case.id for case in dataset.cases],
    )
    arxiv_fetcher = CanonicalArxivFetcher(args.cache_dir.resolve() / "arxiv_cache")
    doi_fetcher = CanonicalDoiFetcher(args.cache_dir.resolve() / "crossref")
    authority = build_authority_index(identities, arxiv_fetcher)
    arxiv_authority = dict(authority)
    authority.update(build_doi_authority_index(ordinary_dois, doi_fetcher))
    arxiv_only_reports = [
        replay_snapshot(snapshot_dir, args.dataset.resolve(), arxiv_authority)
        for snapshot_dir in snapshot_dirs
    ]
    reports = [
        replay_snapshot(snapshot_dir, args.dataset.resolve(), authority)
        for snapshot_dir in snapshot_dirs
    ]
    promotion = evaluate_promotion(
        snapshot_dirs,
        reports,
        authority_identity_count=len(authority),
        claimed_identity_count=len(identities) + len(ordinary_dois),
    )
    doi_incremental_comparison = compare_candidate_reports(arxiv_only_reports, reports)
    output = {
        "report_version": "1.0",
        "claimed_identity_count": len(identities) + len(ordinary_dois),
        "claimed_arxiv_identity_count": len(identities),
        "claimed_doi_identity_count": len(ordinary_dois),
        "resolved_identity_count": len(authority),
        "not_found_identity_count": arxiv_fetcher.not_found_count + doi_fetcher.not_found_count,
        "authority_records": [
            {
                "canonical_identity": identity,
                "status": (
                    "NOT_FOUND"
                    if paper.get("canonical_lookup_status") == "NOT_FOUND"
                    else "RESOLVED"
                ),
                "canonical_title": paper.get("title", ""),
            }
            for identity, paper in sorted(authority.items())
        ],
        "arxiv_not_found_identity_count": arxiv_fetcher.not_found_count,
        "doi_not_found_identity_count": doi_fetcher.not_found_count,
        "doi_failed_identity_count": doi_fetcher.failed_count,
        "actual_api_call_count": arxiv_fetcher.actual_api_call_count + doi_fetcher.actual_api_call_count,
        "cache_hit_count": arxiv_fetcher.cache_hit_count + doi_fetcher.cache_hit_count,
        "snapshots": reports,
        "arxiv_only_snapshots": arxiv_only_reports,
        "doi_incremental_comparison": doi_incremental_comparison,
        "promotion": promotion,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.output_dir / "latest_canonical_metadata_eval.json"
    output_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f"arxiv={len(identities)} doi={len(ordinary_dois)} resolved={len(authority)} "
        f"api_calls={arxiv_fetcher.actual_api_call_count + doi_fetcher.actual_api_call_count} "
        f"cache_hits={arxiv_fetcher.cache_hit_count + doi_fetcher.cache_hit_count}"
    )
    for report in reports:
        summary = report["summary"]
        print(
            f"{report['snapshot_id']}: recall={summary['mean_recall_at_5']:.4f} "
            f"mrr={summary['mean_mrr_at_5']:.4f} "
            f"ndcg={summary['mean_ndcg_at_5']:.4f} "
            f"quarantined={summary['total_metadata_quarantined_count']}"
        )
    print(
        f"promotion_ready={promotion['promotion_ready']} "
        f"blockers={','.join(promotion['promotion_blockers']) or 'none'}"
    )
    print(f"Report written to: {output_path}")


if __name__ == "__main__":
    main()
