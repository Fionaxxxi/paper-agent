"""Run pytest and write machine-readable and tabular local test reports."""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

try:
    from scripts.test_case_catalog import get_test_case_description
except ModuleNotFoundError:  # Supports: python scripts/run_tests_with_report.py
    from test_case_catalog import get_test_case_description


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "test_reports"
DETAIL_COLUMNS = (
    "test_file",
    "test_name",
    "class_name",
    "scenario",
    "purpose",
    "passed_meaning",
    "failed_meaning",
    "status",
    "duration_seconds",
    "message",
)
_UNICODE_ESCAPE = re.compile(r"\\u([0-9a-fA-F]{4})")
HISTORY_COLUMNS = (
    "run_at",
    "git_commit",
    "total",
    "passed",
    "failed",
    "errors",
    "skipped",
    "pass_rate_pct",
    "duration_seconds",
    "pytest_exit_code",
)


def _status_and_message(test_case: ET.Element) -> tuple[str, str, str]:
    for status, tag in (("failed", "failure"), ("error", "error"), ("skipped", "skipped")):
        element = test_case.find(tag)
        if element is not None:
            message = element.attrib.get("message", "").strip()
            details = (element.text or "").strip()
            return status, message, details
    return "passed", "", ""


def _test_file(test_case: ET.Element) -> str:
    explicit_file = test_case.attrib.get("file")
    if explicit_file:
        return explicit_file.replace("\\", "/")
    class_name = test_case.attrib.get("classname", "")
    if not class_name:
        return ""
    return class_name.replace(".", "/") + ".py"


def _decode_scenario(test_name: str) -> str:
    if "[" not in test_name or not test_name.endswith("]"):
        return "默认场景"
    scenario = test_name.split("[", 1)[1][:-1]
    return _UNICODE_ESCAPE.sub(lambda match: chr(int(match.group(1), 16)), scenario)


def parse_junit_xml(xml_path: Path) -> list[dict[str, Any]]:
    """Parse pytest JUnit XML into one normalized row per test case."""
    root = ET.parse(xml_path).getroot()
    rows: list[dict[str, Any]] = []
    for test_case in root.iter("testcase"):
        status, message, details = _status_and_message(test_case)
        test_file = _test_file(test_case)
        test_name = test_case.attrib.get("name", "")
        description = get_test_case_description(test_file, test_name)
        rows.append(
            {
                "test_file": test_file,
                "test_name": test_name,
                "class_name": test_case.attrib.get("classname", ""),
                "scenario": _decode_scenario(test_name),
                "purpose": (
                    description["purpose"] if description else "未登记测试作用"
                ),
                "passed_meaning": (
                    description["passed_meaning"] if description else "未登记通过含义"
                ),
                "failed_meaning": (
                    description["failed_meaning"] if description else "未登记失败含义"
                ),
                "description_registered": description is not None,
                "status": status,
                "duration_seconds": round(float(test_case.attrib.get("time", "0") or 0), 6),
                "message": message,
                "details": details,
            }
        )
    return rows


def summarize(rows: Iterable[dict[str, Any]], pytest_exit_code: int) -> dict[str, Any]:
    """Calculate report-level metrics from normalized test rows."""
    materialized = list(rows)
    counts = {
        "passed": sum(row["status"] == "passed" for row in materialized),
        "failed": sum(row["status"] == "failed" for row in materialized),
        "errors": sum(row["status"] == "error" for row in materialized),
        "skipped": sum(row["status"] == "skipped" for row in materialized),
    }
    total = len(materialized)
    pass_rate = (counts["passed"] / total * 100) if total else 0.0
    return {
        "total": total,
        **counts,
        "description_missing_count": sum(
            row.get("description_registered") is False for row in materialized
        ),
        "pass_rate_pct": round(pass_rate, 2),
        "duration_seconds": round(
            sum(float(row["duration_seconds"]) for row in materialized), 3
        ),
        "pytest_exit_code": pytest_exit_code,
    }


def get_git_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def _write_csv(path: Path, rows: Iterable[dict[str, Any]], columns: tuple[str, ...]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _append_history(path: Path, summary: dict[str, Any], run_at: str, commit: str) -> None:
    write_header = not path.exists()
    with path.open("a", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=HISTORY_COLUMNS,
            extrasaction="ignore",
        )
        if write_header:
            writer.writeheader()
        writer.writerow({"run_at": run_at, "git_commit": commit, **summary})


def _read_history(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def save_report(
    rows: list[dict[str, Any]],
    pytest_exit_code: int,
    output_dir: Path,
    run_at: datetime,
    junit_path: Path,
) -> tuple[dict[str, Any], Path]:
    """Save timestamped/latest JSON and CSV files and update run history."""
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = run_at.strftime("%Y%m%d_%H%M%S")
    run_at_text = run_at.isoformat(timespec="seconds")
    git_commit = get_git_commit()
    summary = summarize(rows, pytest_exit_code)
    history_path = output_dir / "test_history.csv"
    _append_history(history_path, summary, run_at_text, git_commit)

    report = {
        "report_version": "1.0",
        "run_at": run_at_text,
        "git_commit": git_commit,
        "environment": {
            "python_executable": sys.executable,
            "python_version": sys.version.split()[0],
            "platform": sys.platform,
        },
        "summary": summary,
        "tests": rows,
        "history": _read_history(history_path),
    }
    timestamped_json = output_dir / f"test_results_{timestamp}.json"
    latest_json = output_dir / "latest_test_results.json"
    timestamped_csv = output_dir / f"test_details_{timestamp}.csv"
    latest_csv = output_dir / "latest_test_details.csv"
    timestamped_junit = output_dir / f"junit_{timestamp}.xml"
    latest_junit = output_dir / "latest_junit.xml"

    serialized = json.dumps(report, ensure_ascii=False, indent=2)
    timestamped_json.write_text(serialized, encoding="utf-8")
    latest_json.write_text(serialized, encoding="utf-8")
    _write_csv(timestamped_csv, rows, DETAIL_COLUMNS)
    _write_csv(latest_csv, rows, DETAIL_COLUMNS)
    shutil.copyfile(junit_path, timestamped_junit)
    shutil.copyfile(junit_path, latest_junit)
    return report, latest_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run pytest and generate JSON/CSV/JUnit test report data."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Report directory (default: outputs/test_reports).",
    )
    return parser


def main() -> int:
    args, pytest_args = build_parser().parse_known_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    run_at = datetime.now().astimezone()
    temp_junit = output_dir / ".current_junit.xml"
    if pytest_args[:1] == ["--"]:
        pytest_args = pytest_args[1:]

    command = [
        sys.executable,
        "-m",
        "pytest",
        *pytest_args,
        f"--junitxml={temp_junit}",
    ]
    print(f"Running: {' '.join(command)}")
    completed = subprocess.run(command, cwd=PROJECT_ROOT, check=False)
    if not temp_junit.exists():
        print("pytest did not create JUnit XML; no report could be generated.", file=sys.stderr)
        return completed.returncode

    rows = parse_junit_xml(temp_junit)
    report, latest_json = save_report(
        rows,
        completed.returncode,
        output_dir,
        run_at,
        temp_junit,
    )
    temp_junit.unlink(missing_ok=True)
    summary = report["summary"]
    print(
        "Test report: "
        f"{summary['passed']}/{summary['total']} passed, "
        f"{summary['failed']} failed, {summary['errors']} errors, "
        f"{summary['skipped']} skipped."
    )
    if summary["description_missing_count"]:
        print(
            f"ERROR: {summary['description_missing_count']} test cases have no catalog description.",
            file=sys.stderr,
        )
    print(f"Structured report: {latest_json}")
    print(f"Excel-ready table: {output_dir / 'latest_test_details.csv'}")
    return completed.returncode or int(summary["description_missing_count"] > 0)


if __name__ == "__main__":
    raise SystemExit(main())
