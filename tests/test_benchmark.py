import json

import pytest

from eval_harness.benchmark import (
    build_benchmark_report,
    compare_profiles,
    run_profile,
    write_report,
)


def test_baseline_and_candidate_cover_the_same_modules():
    baseline = run_profile("baseline")
    candidate = run_profile("candidate")

    assert baseline.keys() == candidate.keys()
    assert set(candidate) == {
        "intent_router",
        "query_planning",
        "result_merger",
        "retry_router",
        "llm_usage",
        "tool_execution",
        "multi_source_retrieval",
    }


def test_candidate_improves_deterministic_router_and_merger_accuracy():
    baseline = run_profile("baseline")
    candidate = run_profile("candidate")

    assert (
        candidate["intent_router"]["accuracy_pct"]
        > baseline["intent_router"]["accuracy_pct"]
    )
    assert (
        candidate["result_merger"]["accuracy_pct"]
        > baseline["result_merger"]["accuracy_pct"]
    )
    assert (
        candidate["retry_router"]["route_accuracy_pct"]
        > baseline["retry_router"]["route_accuracy_pct"]
    )
    assert (
        candidate["llm_usage"]["tracking_accuracy_pct"]
        > baseline["llm_usage"]["tracking_accuracy_pct"]
    )


def test_query_plan_benchmark_avoids_unnecessary_simple_queries():
    candidate = run_profile("candidate")

    assert candidate["query_planning"]["unnecessary_simple_queries"] == 0
    assert candidate["query_planning"]["plan_accuracy_pct"] == 100.0
    assert candidate["query_planning"]["total_planned_queries"] == 17


def test_comparison_reports_baseline_candidate_and_delta():
    baseline = run_profile("baseline")
    candidate = run_profile("candidate")

    comparison = compare_profiles(baseline, candidate)
    accuracy = comparison["intent_router"]["accuracy_pct"]

    assert accuracy == {
        "baseline": 40.0,
        "candidate": 100.0,
        "delta": 60.0,
    }


def test_llm_usage_benchmark_tracks_success_failure_and_tokens():
    candidate = run_profile("candidate")
    usage = candidate["llm_usage"]

    assert usage["tracking_accuracy_pct"] == 100.0
    assert usage["tracked_call_count"] == 3
    assert usage["tracked_failed_call_count"] == 1
    assert usage["tracked_input_tokens"] == 120
    assert usage["tracked_output_tokens"] == 45
    assert usage["tracked_total_tokens"] == 165


def test_tool_execution_benchmark_measures_contracts_errors_and_recovery():
    baseline = run_profile("baseline")["tool_execution"]
    candidate = run_profile("candidate")["tool_execution"]

    assert baseline["execution_accuracy_pct"] == 16.67
    assert candidate["execution_accuracy_pct"] == 100.0
    assert candidate["structured_error_count"] == 4
    assert candidate["invalid_input_block_count"] == 1
    assert candidate["invalid_output_block_count"] == 1
    assert candidate["permission_block_count"] == 1
    assert candidate["recovered_retry_count"] == 1


def test_multi_source_benchmark_measures_coverage_deduplication_and_recovery():
    baseline = run_profile("baseline")["multi_source_retrieval"]
    candidate = run_profile("candidate")["multi_source_retrieval"]

    assert baseline["retrieval_accuracy_pct"] == 0.0
    assert candidate["retrieval_accuracy_pct"] == 100.0
    assert candidate["provider_call_count"] == 6
    assert candidate["remaining_duplicate_count"] == 0
    assert candidate["partial_failure_recovery_count"] == 1
    assert candidate["structured_failure_count"] == 1


def test_benchmark_report_can_be_written_as_utf8_json(tmp_path):
    report = build_benchmark_report()
    output_path = tmp_path / "benchmark.json"

    write_report(report, output_path)
    loaded = json.loads(output_path.read_text(encoding="utf-8"))

    assert loaded["benchmark_version"] == "1.0"
    assert loaded["mode"] == "offline_deterministic"
    assert loaded["profiles"]["candidate"]["intent_router"]["case_count"] == 10


def test_unknown_profile_is_rejected():
    with pytest.raises(ValueError, match="unknown benchmark profile"):
        run_profile("unknown")
