import json
import time

import pytest

from eval_harness.parallel_retrieval_online import run_online_ab, write_report


def _runner(query, state):
    parallel = __import__("core.config", fromlist=["settings"]).settings.MULTI_SOURCE_PARALLEL_ENABLED
    time.sleep(0.003 if parallel else 0.03)
    documents = [{"title": f"{query} paper", "entry_id": query}]
    return {
        "documents": documents,
        "source_statuses": [{"provider": "arxiv"}, {"provider": "openalex"}],
        "tool_executions": [{"tool_success": True}],
    }


def test_online_parallel_ab_reports_latency_equivalence_and_gate():
    report = run_online_ab(["q1", "q2"], repetitions=2, runner=_runner)

    assert report["summary"]["request_count"] == 8
    assert report["summary"]["parallel_p95_seconds"] < report["summary"]["serial_p95_seconds"]
    assert report["summary"]["mean_result_overlap_rate"] == 1.0
    assert report["summary"]["acceptance_passed"] is True


def test_online_parallel_ab_counts_rate_limit_and_blocks_gate():
    def limited_runner(query, state):
        result = _runner(query, state)
        result["tool_executions"] = [{"tool_success": False, "tool_error_code": "RATE_LIMITED"}]
        return result

    report = run_online_ab(["q"], runner=limited_runner)

    assert report["summary"]["rate_limited_count"] == 4
    assert report["summary"]["acceptance_passed"] is False


def test_online_parallel_ab_blocks_equal_fallback_results_after_network_failure():
    def failed_runner(query, state):
        result = _runner(query, state)
        result["tool_executions"] = [
            {"tool_success": False, "tool_error_code": "NETWORK_ERROR"}
        ]
        return result

    report = run_online_ab(["q"], repetitions=1, runner=failed_runner)

    assert report["summary"]["mean_result_overlap_rate"] == 1.0
    assert report["summary"]["failure_count"] == 2
    assert report["summary"]["acceptance_passed"] is False


def test_online_parallel_ab_rejects_invalid_budget_and_writes_report(tmp_path):
    with pytest.raises(ValueError):
        run_online_ab([], runner=_runner)
    path = write_report(run_online_ab(["q"], repetitions=1, runner=_runner), tmp_path / "report.json")
    assert json.loads(path.read_text(encoding="utf-8"))["summary"]["query_count"] == 1
