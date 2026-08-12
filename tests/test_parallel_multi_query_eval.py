from eval_harness.parallel_multi_query_eval import build_report


def test_multi_query_parallel_benchmark_reports_gate_and_equivalence():
    report = build_report(repetitions=3)

    assert report["result_equality_rate"] == 1.0
    assert report["planned_order_preserved"] is True
    assert report["acceptance_passed"] is (
        report["speedup"] >= 1.3
        and report["latency_reduction_pct"] >= 20
        and report["result_equality_rate"] == 1.0
        and report["planned_order_preserved"]
    )
