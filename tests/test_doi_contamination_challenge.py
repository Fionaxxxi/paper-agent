from eval_harness.doi_contamination_challenge import run_challenge


def test_doi_contamination_challenge_meets_stop_condition():
    report = run_challenge()

    assert report["acceptance_passed"] is True
    assert report["repair_accuracy"] == 1.0
    assert report["false_repair_count"] == 0
    assert report["false_quarantine_count"] == 0
