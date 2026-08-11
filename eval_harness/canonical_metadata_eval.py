"""Replay retrieval snapshots with canonical arXiv identity evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from eval_harness.retrieval_eval_models import load_retrieval_dataset
from eval_harness.retrieval_online import evaluate_case_profile, summarize_profile
from retrieval.metadata_resolver import extract_arxiv_ids
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
    fetcher = CanonicalArxivFetcher(args.cache_dir.resolve())
    authority = build_authority_index(identities, fetcher)
    reports = [
        replay_snapshot(snapshot_dir, args.dataset.resolve(), authority)
        for snapshot_dir in snapshot_dirs
    ]
    output = {
        "report_version": "1.0",
        "claimed_identity_count": len(identities),
        "resolved_identity_count": len(authority),
        "not_found_identity_count": fetcher.not_found_count,
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
        "actual_api_call_count": fetcher.actual_api_call_count,
        "cache_hit_count": fetcher.cache_hit_count,
        "snapshots": reports,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.output_dir / "latest_canonical_metadata_eval.json"
    output_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f"identities={len(identities)} resolved={len(authority)} "
        f"api_calls={fetcher.actual_api_call_count} cache_hits={fetcher.cache_hit_count}"
    )
    for report in reports:
        summary = report["summary"]
        print(
            f"{report['snapshot_id']}: recall={summary['mean_recall_at_5']:.4f} "
            f"mrr={summary['mean_mrr_at_5']:.4f} "
            f"ndcg={summary['mean_ndcg_at_5']:.4f} "
            f"quarantined={summary['total_metadata_quarantined_count']}"
        )
    print(f"Report written to: {output_path}")


if __name__ == "__main__":
    main()
