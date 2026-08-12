from eval_harness.parallel_multi_query_eval import build_report


def test_multi_query_parallel_benchmark_meets_latency_and_equivalence_gate():
    report = build_report(repetitions=3)

    assert report["speedup"] >= 1.3
    assert report["latency_reduction_pct"] >= 20
    assert report["result_equality_rate"] == 1.0
    assert report["planned_order_preserved"] is True
    assert report["acceptance_passed"] is True
