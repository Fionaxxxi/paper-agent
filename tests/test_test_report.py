from pathlib import Path

from scripts.run_tests_with_report import parse_junit_xml, summarize


def test_parse_junit_xml_normalizes_status_duration_and_message(tmp_path: Path):
    junit = tmp_path / "junit.xml"
    junit.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite tests="4">
    <testcase classname="tests.test_demo" name="test_pass" time="0.1"/>
    <testcase classname="tests.test_demo" name="test_fail" time="0.2">
      <failure message="assertion failed">traceback</failure>
    </testcase>
    <testcase classname="tests.test_demo" name="test_error" time="0.3">
      <error message="setup error">details</error>
    </testcase>
    <testcase classname="tests.test_demo" name="test_skip" time="0.4">
      <skipped message="not supported"/>
    </testcase>
  </testsuite>
</testsuites>""",
        encoding="utf-8",
    )

    rows = parse_junit_xml(junit)

    assert [row["status"] for row in rows] == [
        "passed",
        "failed",
        "error",
        "skipped",
    ]
    assert rows[0]["test_file"] == "tests/test_demo.py"
    assert rows[1]["message"] == "assertion failed"
    assert rows[1]["details"] == "traceback"
    assert rows[3]["duration_seconds"] == 0.4
    assert rows[0]["scenario"] == "默认场景"
    assert rows[0]["description_registered"] is False


def test_summarize_calculates_counts_rate_and_duration():
    rows = [
        {"status": "passed", "duration_seconds": 0.125},
        {"status": "passed", "duration_seconds": 0.25},
        {"status": "failed", "duration_seconds": 0.5},
        {"status": "skipped", "duration_seconds": 0.0},
    ]

    summary = summarize(rows, pytest_exit_code=1)

    assert summary == {
        "total": 4,
        "passed": 2,
        "failed": 1,
        "errors": 0,
        "skipped": 1,
        "description_missing_count": 0,
        "pass_rate_pct": 50.0,
        "duration_seconds": 0.875,
        "pytest_exit_code": 1,
    }
