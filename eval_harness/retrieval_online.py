"""Online arXiv/OpenAlex retrieval benchmark with reusable provider results."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from core.config import settings
from eval_harness.retrieval_eval_models import (
    RetrievalEvalCase,
    RetrievalEvalDataset,
    load_retrieval_dataset,
)
from eval_harness.retrieval_metrics import (
    calculate_case_metrics,
    duplicate_rate,
    gold_identity_title_conflict,
    match_relevant_paper,
)
from retrieval.result_merger import merge_documents_with_stats
from retrieval.reranker import rerank_documents_with_stats
from tools.runtime import build_default_tool_runtime


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET_PATH = PROJECT_ROOT / "eval_harness" / "datasets" / "retrieval_online_v1.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "eval_harness" / "reports" / "retrieval_online"
SUPPORTED_PROFILES = (
    "arxiv", "openalex", "multi", "multi_rerank", "multi_verified_rerank",
)


def get_git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def percentile(values: list[float], percentile_value: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round((len(ordered) - 1) * percentile_value)))
    return round(ordered[index], 6)


def mean(values: Iterable[float]) -> float:
    materialized = list(values)
    return round(statistics.fmean(materialized), 6) if materialized else 0.0


class NativeProviderFetcher:
    """Fetch each provider once per case and reuse the result across profiles."""

    def __init__(
        self,
        cache_dir: Path,
        *,
        refresh: bool = False,
        allow_openalex_without_key: bool = False,
        arxiv_interval_seconds: float = 6.0,
        rate_limit_cooldown_seconds: float = 30.0,
        rate_limit_retries: int = 2,
    ) -> None:
        _, self.router, self.executor = build_default_tool_runtime()
        self.cache_dir = cache_dir
        self.refresh = refresh
        self.allow_openalex_without_key = allow_openalex_without_key
        self.arxiv_interval_seconds = max(0.0, arxiv_interval_seconds)
        self.rate_limit_cooldown_seconds = max(0.0, rate_limit_cooldown_seconds)
        self.rate_limit_retries = max(0, rate_limit_retries)
        self.actual_api_call_count = 0
        self.cache_hit_count = 0
        self._last_arxiv_request_at: float | None = None

    def _wait_before_request(self, provider: str) -> None:
        if provider != "arxiv" or self._last_arxiv_request_at is None:
            return
        elapsed = time.monotonic() - self._last_arxiv_request_at
        remaining = self.arxiv_interval_seconds - elapsed
        if remaining > 0:
            time.sleep(remaining)

    @staticmethod
    def _is_rate_limited(error_code: str, error_message: str) -> bool:
        message = error_message.lower()
        return error_code == "RATE_LIMITED" or "http 429" in message

    def fetch(
        self,
        case: RetrievalEvalCase,
        provider: str,
        max_results: int,
    ) -> dict[str, Any]:
        cache_path = self.cache_dir / provider / f"{case.id}.json"
        if cache_path.exists() and not self.refresh:
            payload = json.loads(cache_path.read_text(encoding="utf-8"))
            payload["cache_hit"] = True
            payload["served_latency_seconds"] = 0.0
            self.cache_hit_count += 1
            return payload

        if (
            provider == "openalex"
            and not settings.OPENALEX_API_KEY.strip()
            and not self.allow_openalex_without_key
        ):
            return {
                "provider": provider,
                "success": False,
                "skipped": True,
                "error_code": "MISSING_API_KEY",
                "error_message": "OPENALEX_API_KEY is not configured",
                "papers": [],
                "attempt_count": 0,
                "network_latency_seconds": 0.0,
                "served_latency_seconds": 0.0,
                "cache_hit": False,
            }

        tool_name = self.router.resolve("paper.search", provider)
        rate_limit_retry_count = 0
        while True:
            self._wait_before_request(provider)
            self.actual_api_call_count += 1
            if provider == "arxiv":
                self._last_arxiv_request_at = time.monotonic()
            result = self.executor.execute(
                tool_name,
                {"query": case.query, "max_results": max_results},
            )
            if result.success or not self._is_rate_limited(
                result.error_code,
                result.error_message,
            ):
                break
            if rate_limit_retry_count >= self.rate_limit_retries:
                break
            rate_limit_retry_count += 1
            time.sleep(self.rate_limit_cooldown_seconds)
        papers = (
            result.data.get("papers", [])
            if result.success and isinstance(result.data, dict)
            else []
        )
        payload = {
            "provider": provider,
            "success": result.success,
            "skipped": False,
            "error_code": result.error_code,
            "error_message": result.error_message,
            "papers": papers,
            "attempt_count": result.attempt_count,
            "rate_limit_retry_count": rate_limit_retry_count,
            "network_latency_seconds": result.latency_seconds,
            "served_latency_seconds": result.latency_seconds,
            "cache_hit": False,
        }
        if result.success:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        return payload


def _profile_providers(profile: str) -> tuple[str, ...]:
    if profile in {"multi", "multi_rerank", "multi_verified_rerank"}:
        return ("arxiv", "openalex")
    if profile in {"arxiv", "openalex"}:
        return (profile,)
    raise ValueError(f"unsupported retrieval profile: {profile}")


def _ranked_papers(
    case: RetrievalEvalCase,
    papers: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    ranked = []
    for rank, paper in enumerate(papers, start=1):
        gold_index, relevance_grade = match_relevant_paper(
            paper,
            case.relevant_papers,
        )
        metadata_warnings = list(paper.get("metadata_warnings", []))
        if any(
            gold_identity_title_conflict(paper, relevant)
            for relevant in case.relevant_papers
        ):
            metadata_warnings.append("GOLD_TITLE_CONFLICT")
        ranked.append(
            {
                "rank": rank,
                "title": paper.get("title", ""),
                "source": paper.get("source", ""),
                "entry_id": paper.get("entry_id", ""),
                "doi": paper.get("doi", ""),
                "pdf_url": paper.get("pdf_url", ""),
                "cited_by_count": paper.get("cited_by_count", 0),
                "is_relevant": gold_index is not None,
                "relevance_grade": relevance_grade,
                "matched_gold_title": (
                    case.relevant_papers[gold_index].title
                    if gold_index is not None
                    else ""
                ),
                "ranking_score": paper.get("ranking_score", 0.0),
                "ranking_signals": paper.get("ranking_signals", {}),
                "metadata_warnings": metadata_warnings,
                "metadata_repairs": paper.get("metadata_repairs", []),
                "metadata_resolution_status": paper.get(
                    "metadata_resolution_status", "NOT_APPLIED"
                ),
                "metadata_resolution_action": paper.get(
                    "metadata_resolution_action", "KEEP"
                ),
                "canonical_identity": paper.get("canonical_identity", ""),
                "sources": paper.get("sources", [paper.get("source", "")]),
            }
        )
    return ranked


def evaluate_case_profile(
    case: RetrievalEvalCase,
    profile: str,
    provider_results: dict[str, dict[str, Any]],
    k_values: list[int],
) -> dict[str, Any]:
    providers = _profile_providers(profile)
    selected = [provider_results[provider] for provider in providers]
    groups = [result["papers"] for result in selected if result["success"]]
    raw_count = sum(len(group) for group in groups)
    if profile in {"multi_rerank", "multi_verified_rerank"}:
        merged = rerank_documents_with_stats(
            query=case.query,
            document_groups=groups,
            max_documents=max(k_values),
            metadata_resolution_enabled=profile == "multi_verified_rerank",
        )
    else:
        merged = merge_documents_with_stats(groups, max_documents=max(k_values))
    papers = merged["documents"]
    quality_metrics = calculate_case_metrics(case, papers, k_values)
    failures = [result for result in selected if not result["success"]]
    skipped = [result for result in failures if result.get("skipped")]
    hard_failures = [result for result in failures if not result.get("skipped")]

    if papers and (hard_failures or skipped):
        status = "partial_success"
    elif papers:
        status = "success"
    elif hard_failures:
        status = "failed"
    elif any(result["success"] for result in selected):
        status = "empty"
    elif skipped and len(skipped) == len(selected):
        status = "skipped"
    else:
        status = "failed"

    ranked_papers = _ranked_papers(case, papers)
    return {
        "case_id": case.id,
        "query": case.query,
        "language": case.language,
        "category": case.category,
        "difficulty": case.difficulty,
        "profile": profile,
        "status": status,
        "providers": list(providers),
        "provider_errors": [
            {
                "provider": result["provider"],
                "error_code": result["error_code"],
                "error_message": result["error_message"],
            }
            for result in failures
        ],
        "provider_call_count": len([result for result in selected if not result.get("skipped")]),
        "cache_hit_count": sum(result.get("cache_hit", False) for result in selected),
        "network_latency_seconds": round(
            sum(result["network_latency_seconds"] for result in selected),
            6,
        ),
        "served_latency_seconds": round(
            sum(result["served_latency_seconds"] for result in selected),
            6,
        ),
        "raw_document_count": raw_count,
        "merged_document_count": len(papers),
        "duplicate_rate_pct": duplicate_rate(raw_count, len(papers)),
        "candidate_count_before_top_k": merged.get(
            "candidate_count_before_top_k",
            len(papers),
        ),
        "metadata_warning_count": sum(
            bool(paper.get("metadata_warnings")) for paper in ranked_papers
        ),
        "metadata_repaired_count": merged.get("metadata_repaired_count", 0),
        "metadata_quarantined_count": merged.get("metadata_quarantined_count", 0),
        "quarantined_documents": merged.get("quarantined_documents", []),
        "ranking_strategy": merged.get("ranking_strategy", "source_priority"),
        **quality_metrics,
        "ranked_papers": ranked_papers,
    }


def summarize_profile(
    profile: str,
    case_results: list[dict[str, Any]],
    k_values: list[int],
) -> dict[str, Any]:
    latencies = [
        result["network_latency_seconds"]
        for result in case_results
        if result["status"] not in {"skipped"}
    ]
    summary = {
        "profile": profile,
        "case_count": len(case_results),
        "success_count": sum(result["status"] == "success" for result in case_results),
        "partial_success_count": sum(
            result["status"] == "partial_success" for result in case_results
        ),
        "failed_count": sum(result["status"] == "failed" for result in case_results),
        "empty_count": sum(result["status"] == "empty" for result in case_results),
        "skipped_count": sum(result["status"] == "skipped" for result in case_results),
        "empty_result_rate_pct": round(
            sum(result["returned_count"] == 0 for result in case_results)
            / len(case_results)
            * 100,
            2,
        ),
        "failure_rate_pct": round(
            sum(result["status"] == "failed" for result in case_results)
            / len(case_results)
            * 100,
            2,
        ),
        "average_dimension_coverage_pct": mean(
            result["dimension_coverage_pct"] for result in case_results
        ),
        "average_duplicate_rate_pct": mean(
            result["duplicate_rate_pct"] for result in case_results
        ),
        "total_metadata_warning_count": sum(
            result.get("metadata_warning_count", 0) for result in case_results
        ),
        "total_metadata_repaired_count": sum(
            result.get("metadata_repaired_count", 0) for result in case_results
        ),
        "total_metadata_quarantined_count": sum(
            result.get("metadata_quarantined_count", 0) for result in case_results
        ),
        "total_provider_calls": sum(result["provider_call_count"] for result in case_results),
        "total_cache_hits": sum(result["cache_hit_count"] for result in case_results),
        "p50_network_latency_seconds": percentile(latencies, 0.5),
        "p95_network_latency_seconds": percentile(latencies, 0.95),
    }
    for k in sorted(k_values):
        for metric in ("recall", "precision", "mrr", "ndcg"):
            key = f"{metric}_at_{k}"
            summary[f"mean_{key}"] = mean(result[key] for result in case_results)
    return summary


def run_online_benchmark(
    dataset: RetrievalEvalDataset,
    fetcher,
    profiles: list[str],
) -> dict[str, Any]:
    unknown_profiles = sorted(set(profiles) - set(SUPPORTED_PROFILES))
    if unknown_profiles:
        raise ValueError(f"unsupported retrieval profiles: {unknown_profiles}")

    required_providers = sorted(
        {provider for profile in profiles for provider in _profile_providers(profile)}
    )
    max_results = max(dataset.k_values)
    provider_results_by_case = {}
    for case in dataset.cases:
        provider_results_by_case[case.id] = {
            provider: fetcher.fetch(case, provider, max_results)
            for provider in required_providers
        }

    profiles_payload = {}
    for profile in profiles:
        case_results = [
            evaluate_case_profile(
                case,
                profile,
                provider_results_by_case[case.id],
                dataset.k_values,
            )
            for case in dataset.cases
        ]
        profiles_payload[profile] = {
            "summary": summarize_profile(profile, case_results, dataset.k_values),
            "cases": case_results,
        }

    return {
        "report_version": "1.1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": get_git_commit(),
        "dataset_name": dataset.dataset_name,
        "dataset_version": dataset.dataset_version,
        "dataset_case_count": len(dataset.cases),
        "k_values": dataset.k_values,
        "mode": "online_native_tools",
        "profiles": profiles_payload,
        "acquisition": {
            "actual_api_call_count": getattr(fetcher, "actual_api_call_count", 0),
            "provider_cache_hit_count": getattr(fetcher, "cache_hit_count", 0),
            "openalex_api_key_configured": bool(settings.OPENALEX_API_KEY.strip()),
        },
    }


def write_online_report(report: dict[str, Any], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "latest_retrieval_online.json"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    summary_path = output_dir / "latest_retrieval_summary.csv"
    summaries = [payload["summary"] for payload in report["profiles"].values()]
    with summary_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summaries[0]))
        writer.writeheader()
        writer.writerows(summaries)

    case_rows = [
        {key: value for key, value in case.items() if key != "ranked_papers"}
        for payload in report["profiles"].values()
        for case in payload["cases"]
    ]
    case_path = output_dir / "latest_retrieval_cases.csv"
    with case_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(case_rows[0]))
        writer.writeheader()
        writer.writerows(case_rows)

    paper_rows = [
        {
            "profile": case["profile"],
            "case_id": case["case_id"],
            "query": case["query"],
            **paper,
        }
        for payload in report["profiles"].values()
        for case in payload["cases"]
        for paper in case["ranked_papers"]
    ]
    paper_path = output_dir / "latest_retrieval_papers.csv"
    if paper_rows:
        with paper_path.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(paper_rows[0]))
            writer.writeheader()
            writer.writerows(paper_rows)
    return json_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run online paper retrieval evaluation.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--profiles",
        default="arxiv,openalex,multi",
        help=(
            "Comma-separated profiles: arxiv, openalex, multi, multi_rerank, "
            "multi_verified_rerank"
        ),
    )
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--allow-openalex-without-key", action="store_true")
    parser.add_argument("--case-limit", type=int, default=0)
    parser.add_argument("--arxiv-interval", type=float, default=6.0)
    parser.add_argument("--rate-limit-cooldown", type=float, default=30.0)
    parser.add_argument("--rate-limit-retries", type=int, default=2)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    dataset = load_retrieval_dataset(args.dataset.resolve())
    if args.case_limit > 0:
        dataset = dataset.model_copy(update={"cases": dataset.cases[: args.case_limit]})
    profiles = [profile.strip() for profile in args.profiles.split(",") if profile.strip()]
    fetcher = NativeProviderFetcher(
        args.output_dir.resolve() / "provider_cache" / dataset.dataset_version,
        refresh=args.refresh,
        allow_openalex_without_key=args.allow_openalex_without_key,
        arxiv_interval_seconds=args.arxiv_interval,
        rate_limit_cooldown_seconds=args.rate_limit_cooldown,
        rate_limit_retries=args.rate_limit_retries,
    )
    report = run_online_benchmark(dataset, fetcher, profiles)
    output_path = write_online_report(report, args.output_dir.resolve())
    for profile, payload in report["profiles"].items():
        summary = payload["summary"]
        print(
            f"[{profile}] recall@5={summary.get('mean_recall_at_5', 0):.4f} "
            f"mrr@5={summary.get('mean_mrr_at_5', 0):.4f} "
            f"failed={summary['failed_count']} skipped={summary['skipped_count']}"
        )
    print(f"Report written to: {output_path}")


if __name__ == "__main__":
    main()
