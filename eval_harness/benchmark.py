import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List

from pydantic import BaseModel, Field

from agent.router import route_after_evaluate
from eval_harness.benchmark_cases import (
    INTENT_CASES,
    LLM_USAGE_CASES,
    QUERY_PLAN_CASES,
    RESULT_MERGER_CASES,
    RETRY_CASES,
    TOOL_EXECUTION_CASES,
)
from nodes.intent_router import classify_input_intent
from nodes.query_plan import build_rule_based_sub_queries
from retrieval.result_merger import build_document_key, merge_documents_with_stats
from core.llm_usage import build_llm_usage_update
from tools.contracts import RetryPolicy, ToolRiskLevel, ToolSpec
from tools.executor import ToolExecutor
from tools.registry import ToolRegistry


BENCHMARK_VERSION = "1.0"
DEFAULT_OUTPUT_PATH = Path("eval_harness/reports/offline_benchmark.json")


def percentage(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator * 100, 2)


def get_git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def baseline_intent_classifier(state: Dict[str, Any]) -> str:
    return "research"


def baseline_query_planner(state: Dict[str, Any]) -> List[str]:
    query = state.get("rewritten_query") or state.get("query", "")
    return [query] if query else []


def baseline_document_merger(
    document_groups: List[List[Dict[str, Any]]],
    max_documents: int,
) -> Dict[str, Any]:
    documents = [
        document
        for group in document_groups
        for document in group
    ][:max_documents]
    raw_count = sum(len(group) for group in document_groups)
    return {
        "documents": documents,
        "raw_document_count": raw_count,
        "merged_document_count": len(documents),
        "deduplicated_count": 0,
    }


def baseline_retry_router(state: Dict[str, Any]) -> str:
    return "generate"


def baseline_usage_tracker(
    state: Dict[str, Any],
    record: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "llm_call_count": 0,
        "llm_failed_call_count": 0,
        "input_token_usage": 0,
        "output_token_usage": 0,
        "token_usage": 0,
        "llm_usage": [],
    }


class BenchmarkToolInput(BaseModel):
    value: int = Field(ge=1)


class BenchmarkToolOutput(BaseModel):
    doubled: int


def execute_tool_case_behavior(
    behavior: str,
    value: int,
    attempt: int,
) -> Dict[str, Any]:
    if behavior == "execution_error":
        raise ConnectionError("offline benchmark failure")
    if behavior == "fail_once" and attempt == 1:
        raise ConnectionError("temporary offline benchmark failure")
    if behavior == "invalid_output":
        return {"unexpected": value}
    return {"doubled": value * 2}


def baseline_tool_runner(case: Dict[str, Any]) -> Dict[str, Any]:
    """Legacy direct-call behavior without schemas or structured recovery."""

    try:
        execute_tool_case_behavior(
            case["behavior"],
            case["arguments"].get("value", 0),
            1,
        )
        return {"success": True, "error_code": "", "attempt_count": 1}
    except Exception:
        return {"success": False, "error_code": "", "attempt_count": 1}


def candidate_tool_runner(case: Dict[str, Any]) -> Dict[str, Any]:
    attempts = 0

    class BenchmarkTool:
        spec = ToolSpec(
            name="benchmark.tool",
            version="1.0.0",
            description="Offline deterministic benchmark tool.",
            input_model=BenchmarkToolInput,
            output_model=BenchmarkToolOutput,
            provider="offline",
            capabilities=("benchmark",),
            risk_level=ToolRiskLevel(case.get("risk_level", "read_only")),
            timeout_seconds=1.0,
            retry_policy=RetryPolicy(max_attempts=case["max_attempts"]),
        )

        def invoke(self, arguments):
            nonlocal attempts
            attempts += 1
            return execute_tool_case_behavior(
                case["behavior"],
                arguments.value,
                attempts,
            )

    registry = ToolRegistry()
    registry.register(BenchmarkTool())
    result = ToolExecutor(registry).execute(
        "benchmark.tool",
        case["arguments"],
    )
    return {
        "success": result.success,
        "error_code": result.error_code,
        "attempt_count": result.attempt_count,
    }


def count_duplicate_documents(documents: Iterable[Dict[str, Any]]) -> int:
    seen = set()
    duplicates = 0

    for document in documents:
        key = build_document_key(document)
        if not key:
            continue
        if key in seen:
            duplicates += 1
        else:
            seen.add(key)

    return duplicates


def evaluate_intent(
    classifier: Callable[[Dict[str, Any]], str],
) -> Dict[str, Any]:
    case_results = []

    for case in INTENT_CASES:
        state = {
            "query": case["query"],
            "pdf_path": case.get("pdf_path", ""),
        }
        predicted = classifier(state)
        expected = case["expected_intent"]
        case_results.append(
            {
                "id": case["id"],
                "expected": expected,
                "actual": predicted,
                "passed": predicted == expected,
                "short_circuited": predicted != "research",
            }
        )

    passed = sum(1 for result in case_results if result["passed"])
    local_responses = sum(
        1 for result in case_results if result["short_circuited"]
    )
    research_false_blocks = sum(
        1
        for result in case_results
        if result["expected"] == "research" and result["actual"] != "research"
    )

    return {
        "case_count": len(case_results),
        "passed_count": passed,
        "accuracy_pct": percentage(passed, len(case_results)),
        "local_response_count": local_responses,
        "estimated_llm_calls_avoided": local_responses,
        "research_false_block_count": research_false_blocks,
        "cases": case_results,
    }


def evaluate_query_plan(
    planner: Callable[[Dict[str, Any]], List[str]],
) -> Dict[str, Any]:
    case_results = []

    for case in QUERY_PLAN_CASES:
        queries = planner(case)
        actual_multi_query = len(queries) > 1
        expected_multi_query = case["expected_multi_query"]
        case_results.append(
            {
                "id": case["id"],
                "expected_multi_query": expected_multi_query,
                "actual_multi_query": actual_multi_query,
                "query_count": len(queries),
                "passed": actual_multi_query == expected_multi_query,
            }
        )

    passed = sum(1 for result in case_results if result["passed"])
    total_queries = sum(result["query_count"] for result in case_results)
    simple_cases = [
        result
        for result in case_results
        if not result["expected_multi_query"]
    ]
    unnecessary_queries = sum(
        max(result["query_count"] - 1, 0)
        for result in simple_cases
    )

    return {
        "case_count": len(case_results),
        "passed_count": passed,
        "plan_accuracy_pct": percentage(passed, len(case_results)),
        "total_planned_queries": total_queries,
        "average_query_count": round(total_queries / len(case_results), 2),
        "unnecessary_simple_queries": unnecessary_queries,
        "cases": case_results,
    }


def evaluate_result_merger(
    merger: Callable[
        [List[List[Dict[str, Any]]], int],
        Dict[str, Any],
    ],
) -> Dict[str, Any]:
    case_results = []

    for case in RESULT_MERGER_CASES:
        result = merger(case["document_groups"], case["max_documents"])
        documents = result["documents"]
        duplicate_count = count_duplicate_documents(documents)
        expected_unique_count = case["expected_unique_count"]
        passed = (
            len(documents) == expected_unique_count
            and duplicate_count == 0
        )
        case_results.append(
            {
                "id": case["id"],
                "expected_unique_count": expected_unique_count,
                "actual_document_count": len(documents),
                "duplicate_count": duplicate_count,
                "documents_removed": (
                    result["raw_document_count"]
                    - result["merged_document_count"]
                ),
                "passed": passed,
            }
        )

    passed = sum(1 for result in case_results if result["passed"])
    duplicate_count = sum(
        result["duplicate_count"] for result in case_results
    )
    removed = sum(
        result["documents_removed"] for result in case_results
    )

    return {
        "case_count": len(case_results),
        "passed_count": passed,
        "accuracy_pct": percentage(passed, len(case_results)),
        "remaining_duplicate_count": duplicate_count,
        "documents_removed": removed,
        "cases": case_results,
    }


def evaluate_retry_router(
    router: Callable[[Dict[str, Any]], str],
) -> Dict[str, Any]:
    case_results = []

    for case in RETRY_CASES:
        actual = router(case)
        expected = case["expected_route"]
        case_results.append(
            {
                "id": case["id"],
                "expected": expected,
                "actual": actual,
                "passed": actual == expected,
            }
        )

    passed = sum(1 for result in case_results if result["passed"])
    return {
        "case_count": len(case_results),
        "passed_count": passed,
        "route_accuracy_pct": percentage(passed, len(case_results)),
        "retry_count": sum(
            1 for result in case_results if result["actual"] == "retry"
        ),
        "cases": case_results,
    }


def evaluate_llm_usage(
    tracker: Callable[
        [Dict[str, Any], Dict[str, Any]],
        Dict[str, Any],
    ],
) -> Dict[str, Any]:
    case_results = []

    for case in LLM_USAGE_CASES:
        state: Dict[str, Any] = {}
        for record in case["records"]:
            state = {
                **state,
                **tracker(state, record),
            }

        expected = case["expected"]
        actual = {
            key: state.get(key, 0)
            for key in expected
        }
        case_results.append(
            {
                "id": case["id"],
                "expected": expected,
                "actual": actual,
                "passed": actual == expected,
            }
        )

    passed = sum(1 for result in case_results if result["passed"])
    return {
        "case_count": len(case_results),
        "passed_count": passed,
        "tracking_accuracy_pct": percentage(
            passed,
            len(case_results),
        ),
        "tracked_call_count": sum(
            result["actual"]["llm_call_count"]
            for result in case_results
        ),
        "tracked_failed_call_count": sum(
            result["actual"]["llm_failed_call_count"]
            for result in case_results
        ),
        "tracked_input_tokens": sum(
            result["actual"]["input_token_usage"]
            for result in case_results
        ),
        "tracked_output_tokens": sum(
            result["actual"]["output_token_usage"]
            for result in case_results
        ),
        "tracked_total_tokens": sum(
            result["actual"]["token_usage"]
            for result in case_results
        ),
        "cases": case_results,
    }


def evaluate_tool_execution(
    runner: Callable[[Dict[str, Any]], Dict[str, Any]],
) -> Dict[str, Any]:
    case_results = []

    for case in TOOL_EXECUTION_CASES:
        actual = runner(case)
        expected = case["expected"]
        case_results.append(
            {
                "id": case["id"],
                "expected": expected,
                "actual": actual,
                "passed": actual == expected,
            }
        )

    passed = sum(result["passed"] for result in case_results)
    return {
        "case_count": len(case_results),
        "passed_count": passed,
        "execution_accuracy_pct": percentage(passed, len(case_results)),
        "structured_error_count": sum(
            bool(result["actual"]["error_code"])
            for result in case_results
            if not result["actual"]["success"]
        ),
        "invalid_input_block_count": sum(
            result["actual"]["error_code"] == "INVALID_INPUT"
            for result in case_results
        ),
        "invalid_output_block_count": sum(
            result["actual"]["error_code"] == "INVALID_OUTPUT"
            for result in case_results
        ),
        "permission_block_count": sum(
            result["actual"]["error_code"] == "PERMISSION_DENIED"
            for result in case_results
        ),
        "recovered_retry_count": sum(
            result["actual"]["success"]
            and result["actual"]["attempt_count"] > 1
            for result in case_results
        ),
        "cases": case_results,
    }


def run_profile(profile: str) -> Dict[str, Any]:
    if profile == "baseline":
        return {
            "intent_router": evaluate_intent(baseline_intent_classifier),
            "query_planning": evaluate_query_plan(baseline_query_planner),
            "result_merger": evaluate_result_merger(
                baseline_document_merger
            ),
            "retry_router": evaluate_retry_router(baseline_retry_router),
            "llm_usage": evaluate_llm_usage(baseline_usage_tracker),
            "tool_execution": evaluate_tool_execution(baseline_tool_runner),
        }

    if profile == "candidate":
        return {
            "intent_router": evaluate_intent(classify_input_intent),
            "query_planning": evaluate_query_plan(
                build_rule_based_sub_queries
            ),
            "result_merger": evaluate_result_merger(
                lambda groups, limit: merge_documents_with_stats(
                    document_groups=groups,
                    max_documents=limit,
                )
            ),
            "retry_router": evaluate_retry_router(route_after_evaluate),
            "llm_usage": evaluate_llm_usage(build_llm_usage_update),
            "tool_execution": evaluate_tool_execution(candidate_tool_runner),
        }

    raise ValueError(f"unknown benchmark profile: {profile}")


COMPARISON_METRICS = {
    "intent_router": [
        "accuracy_pct",
        "local_response_count",
        "estimated_llm_calls_avoided",
        "research_false_block_count",
    ],
    "query_planning": [
        "plan_accuracy_pct",
        "total_planned_queries",
        "average_query_count",
        "unnecessary_simple_queries",
    ],
    "result_merger": [
        "accuracy_pct",
        "remaining_duplicate_count",
        "documents_removed",
    ],
    "retry_router": [
        "route_accuracy_pct",
        "retry_count",
    ],
    "llm_usage": [
        "tracking_accuracy_pct",
        "tracked_call_count",
        "tracked_failed_call_count",
        "tracked_input_tokens",
        "tracked_output_tokens",
        "tracked_total_tokens",
    ],
    "tool_execution": [
        "execution_accuracy_pct",
        "structured_error_count",
        "invalid_input_block_count",
        "invalid_output_block_count",
        "permission_block_count",
        "recovered_retry_count",
    ],
}


def compare_profiles(
    baseline: Dict[str, Any],
    candidate: Dict[str, Any],
) -> Dict[str, Any]:
    comparison: Dict[str, Any] = {}

    for module, metric_names in COMPARISON_METRICS.items():
        comparison[module] = {}
        for metric_name in metric_names:
            baseline_value = baseline[module][metric_name]
            candidate_value = candidate[module][metric_name]
            comparison[module][metric_name] = {
                "baseline": baseline_value,
                "candidate": candidate_value,
                "delta": round(candidate_value - baseline_value, 2),
            }

    return comparison


def build_benchmark_report() -> Dict[str, Any]:
    baseline = run_profile("baseline")
    candidate = run_profile("candidate")
    return {
        "benchmark_version": BENCHMARK_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": get_git_commit(),
        "mode": "offline_deterministic",
        "profiles": {
            "baseline": baseline,
            "candidate": candidate,
        },
        "comparison": compare_profiles(baseline, candidate),
    }


def write_report(report: Dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def print_comparison(report: Dict[str, Any]) -> None:
    print("\n=== Offline Capability Benchmark ===")
    print(f"Commit: {report['git_commit']}")
    print(f"Mode: {report['mode']}")

    for module, metrics in report["comparison"].items():
        print(f"\n[{module}]")
        for metric_name, values in metrics.items():
            print(
                f"{metric_name}: "
                f"{values['baseline']} -> {values['candidate']} "
                f"(delta={values['delta']})"
            )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run deterministic baseline/candidate benchmarks."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path for the JSON benchmark report.",
    )
    args = parser.parse_args()

    report = build_benchmark_report()
    write_report(report, args.output)
    print_comparison(report)
    print(f"\nReport written to: {args.output}")


if __name__ == "__main__":
    main()
