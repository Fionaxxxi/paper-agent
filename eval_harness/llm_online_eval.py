"""可显式运行、会产生真实 API 费用的在线 LLM 能力评测。"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.config import settings
from nodes.generate import generate_node
from nodes.query_plan import query_plan_node
from nodes.query_rewrite import query_rewrite_node
from nodes.research_analyze import research_analyze_node


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = PROJECT_ROOT / "eval_harness/datasets/llm_core_v1.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "outputs/llm_core_eval"
PLACEHOLDER_KEYS = {"", "your_api_key_here", "sk-xxx", "test"}


def load_dataset(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    ids = [case["id"] for case in payload.get("cases", [])]
    if not payload.get("frozen") or not ids or len(ids) != len(set(ids)):
        raise ValueError("在线数据集必须冻结、非空且 case id 唯一")
    return payload


def materialize_cases(dataset: dict[str, Any]) -> list[dict[str, Any]]:
    """将证据 fixture 展开为运行时 documents，同时保持源数据集紧凑可审计。"""
    fixtures = dataset.get("fixtures", {})
    materialized = []
    for source_case in dataset["cases"]:
        case = dict(source_case)
        fixture_names = case.pop("document_fixtures", [])
        if fixture_names:
            missing = [name for name in fixture_names if name not in fixtures]
            if missing:
                raise ValueError(
                    f"case {case['id']} 引用了未知 fixture: {', '.join(missing)}"
                )
            case["documents"] = [dict(fixtures[name]) for name in fixture_names]
        materialized.append(case)
    return materialized


def _analysis_result(case: dict[str, Any]) -> dict[str, Any]:
    result = research_analyze_node({"query": case["query"], "llm_usage": []})
    expected = case["expected"]
    usage_records = result.get("llm_usage", [])
    actual = {
        "task_level": result.get("task_level"),
        "primary_skill": result.get("research_analysis", {}).get("primary_skill"),
        "plan_valid": result.get("research_plan_validation", {}).get("valid", False),
        "analysis_source": result.get("research_analysis", {}).get("analysis_source"),
        "llm_calls": result.get("llm_call_count", 0),
        "failed_calls": result.get("llm_failed_call_count", 0),
        "tokens": result.get("token_usage", 0),
        "llm_error_types": [
            record.get("error_type", "") for record in usage_records
            if not record.get("success", False)
        ],
        "analysis_parse_error": result.get("paper_metadata", {}).get(
            "research_analysis_parse_error", ""
        ),
        "analysis_raw_response": result.get("paper_metadata", {}).get(
            "research_analysis_raw_response", ""
        ),
    }
    checks = {
        "task_level": actual["task_level"] == expected["task_level"],
        "primary_skill": actual["primary_skill"] == expected["primary_skill"],
        "plan_valid": actual["plan_valid"] == expected["plan_valid"],
        "llm_call_budget": expected["llm_calls_min"] <= actual["llm_calls"] <= expected["llm_calls_max"],
        "no_failed_call": actual["failed_calls"] == 0,
    }
    analysis = result.get("research_analysis", {})
    plan_tasks = result.get("research_plan", {}).get("tasks", [])
    if "requires_report" in expected:
        checks["requires_report"] = analysis.get("requires_report") == expected["requires_report"]
    if "requires_multiple_sources" in expected:
        checks["requires_multiple_sources"] = analysis.get("requires_multiple_sources") == expected["requires_multiple_sources"]
    if "max_plan_tasks" in expected:
        checks["bounded_plan"] = len(plan_tasks) <= expected["max_plan_tasks"]
    if expected.get("objective_any"):
        objective_text = " ".join(analysis.get("objectives", []))
        checks["objective_coverage"] = all(term in objective_text for term in expected["objective_any"])
    if expected.get("dimension_any"):
        dimension_text = " ".join(analysis.get("evaluation_dimensions", []))
        checks["dimension_coverage"] = any(term in dimension_text for term in expected["dimension_any"])
    return {"actual": actual, "checks": checks, "response": result.get("research_analysis", {})}


def _query_planning_result(case: dict[str, Any]) -> dict[str, Any]:
    state: dict[str, Any] = {"query": case["query"], "llm_usage": []}
    state.update(research_analyze_node(state))
    state.update(query_rewrite_node(state))
    result = query_plan_node(state)
    expected = case["expected"]
    count = len(result.get("sub_queries", []))
    actual = {
        "query_count": count,
        "plan_reason": result.get("query_plan_reason"),
        "complexity": result.get("query_complexity"),
        "llm_calls": state.get("llm_call_count", 0),
        "failed_calls": state.get("llm_failed_call_count", 0),
        "tokens": state.get("token_usage", 0),
        "sub_queries": result.get("sub_queries", []),
        "llm_error_types": [
            record.get("error_type", "") for record in state.get("llm_usage", [])
            if not record.get("success", False)
        ],
    }
    checks = {
        "query_count": expected["query_count_min"] <= count <= expected["query_count_max"],
        "llm_call_budget": actual["llm_calls"] <= expected["llm_calls_max"],
        "no_failed_call": actual["failed_calls"] == 0,
    }
    if expected.get("plan_reason"):
        checks["plan_reason"] = actual["plan_reason"] == expected["plan_reason"]
    if expected.get("complexity"):
        checks["complexity"] = actual["complexity"] == expected["complexity"]
    return {"actual": actual, "checks": checks, "response": result.get("sub_queries", [])}


def _generation_result(case: dict[str, Any]) -> dict[str, Any]:
    state = {
        "query": case["query"], "task_type": case["task_type"],
        "task_level": case["task_level"], "documents": case["documents"],
        "retrieval_outcome": "accepted", "llm_usage": [],
        "research_brief": case.get("research_brief", {}),
        "research_analysis": {"primary_skill": case.get("primary_skill", "")},
    }
    result = generate_node(state)
    answer = result.get("answer", "")
    metadata = result.get("paper_metadata", {})
    return _grade_generation(case, answer, metadata, result)


def _grade_generation(
    case: dict[str, Any],
    answer: str,
    metadata: dict[str, Any],
    usage: dict[str, Any],
) -> dict[str, Any]:
    group_checks = [
        any(term.casefold() in answer.casefold() for term in group)
        for group in case.get("required_any", [])
    ]
    title_checks = [title.casefold() in answer.casefold() for title in case.get("required_titles", [])]
    actual = {
        "skill_used": metadata.get("skill_used"),
        "answer_chars": len(answer),
        "required_group_hits": sum(group_checks),
        "required_group_total": len(group_checks),
        "title_hits": sum(title_checks),
        "title_total": len(title_checks),
        "llm_calls": usage.get("llm_call_count", 0),
        "failed_calls": usage.get("llm_failed_call_count", 0),
        "tokens": usage.get("token_usage", 0),
        "llm_error_types": [
            record.get("error_type", "")
            for record in usage.get("llm_usage", [])
            if not record.get("success", False)
        ],
    }
    checks = {
        "skill_route": actual["skill_used"] == case["expected_skill"],
        "minimum_length": len(answer) >= case["min_answer_chars"],
        "required_semantics": all(group_checks),
        "evidence_identity": all(title_checks),
        "one_successful_llm_call": actual["llm_calls"] == 1 and actual["failed_calls"] == 0,
        "not_fallback": "PaperAgent 降级回答" not in answer,
    }
    return {"actual": actual, "checks": checks, "response": answer}


def regrade_report(report: dict[str, Any], dataset: dict[str, Any]) -> dict[str, Any]:
    """使用冻结输入和已有原始输出重新判分，不调用模型。"""
    by_id = {case["id"]: case for case in materialize_cases(dataset)}
    for row in report.get("cases", []):
        case = by_id.get(row["id"])
        if not case:
            continue
        if case["category"] == "generation":
            payload = _grade_generation(
                case, str(row.get("response", "")),
                {"skill_used": row.get("actual", {}).get("skill_used")},
                {"llm_call_count": row.get("actual", {}).get("llm_calls", 0),
                 "llm_failed_call_count": row.get("actual", {}).get("failed_calls", 0),
                 "token_usage": row.get("actual", {}).get("tokens", 0)},
            )
            row.update(payload)
            row["passed"] = all(payload["checks"].values())
        failed_calls = row.get("actual", {}).get("failed_calls", 0)
        row["failure_kind"] = (
            "none" if row.get("passed")
            else "provider" if failed_calls
            else "execution" if row.get("error")
            else "capability"
        )
    cases = report.get("cases", [])
    passed = sum(bool(row.get("passed")) for row in cases)
    report["summary"].update(
        passed_count=passed, failed_count=len(cases) - passed,
        provider_failure_count=sum(
            row.get("failure_kind") == "provider" for row in cases
        ),
        capability_failure_count=sum(
            row.get("failure_kind") == "capability" for row in cases
        ),
        pass_rate_pct=round(passed / len(cases) * 100, 2) if cases else 0,
    )
    report["regraded_at"] = datetime.now(timezone.utc).isoformat()
    return report


def merge_case_results(
    existing_results: list[dict[str, Any]],
    new_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """合并定向重跑；临时 Provider 失败不能覆盖已有能力结论。"""
    replacements = {row["id"]: row for row in new_results}
    merged = []
    for existing_row in existing_results:
        replacement = replacements.get(existing_row["id"])
        if replacement is None:
            merged.append(existing_row)
            continue
        prior_attempts = list(existing_row.get("attempts", []))
        attempt_snapshot = {
            key: value for key, value in replacement.items()
            if key != "attempts"
        }
        if (
            replacement.get("failure_kind") == "provider"
            and existing_row.get("failure_kind") != "provider"
        ):
            selected = dict(existing_row)
        else:
            selected = dict(replacement)
        selected["attempts"] = [*prior_attempts, attempt_snapshot]
        merged.append(selected)
    existing_ids = {row["id"] for row in merged}
    merged.extend(
        row for case_id, row in replacements.items()
        if case_id not in existing_ids
    )
    return merged


def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    started = datetime.now(timezone.utc)
    try:
        runners = {
            "research_analysis": _analysis_result,
            "query_planning": _query_planning_result,
            "generation": _generation_result,
        }
        payload = runners[case["category"]](case)
        error = ""
    except Exception as exc:  # report provider/config failures instead of losing the run
        payload = {"actual": {}, "checks": {"execution": False}, "response": ""}
        error = f"{type(exc).__name__}: {exc}"
    checks = payload["checks"]
    failed_calls = payload["actual"].get("failed_calls", 0)
    failure_kind = (
        "none" if bool(checks) and all(checks.values())
        else "provider" if failed_calls
        else "execution" if error
        else "capability"
    )
    return {
        "id": case["id"], "category": case["category"],
        "description": case["description"], "query": case["query"],
        "passed": bool(checks) and all(checks.values()),
        "checks": checks, "actual": payload["actual"],
        "response": payload["response"], "error": error,
        "failure_kind": failure_kind,
        "duration_seconds": round((datetime.now(timezone.utc) - started).total_seconds(), 3),
    }


def _git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, text=True).strip()
    except Exception:
        return "unknown"


def write_report(report: dict[str, Any], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    timestamped = output_dir / f"llm_online_{stamp}.json"
    latest = output_dir / "latest_llm_online.json"
    serialized = json.dumps(report, ensure_ascii=False, indent=2)
    timestamped.write_text(serialized, encoding="utf-8")
    latest.write_text(serialized, encoding="utf-8")
    columns = ["id", "category", "description", "passed", "duration_seconds", "llm_calls", "tokens", "failed_calls", "error"]
    with (output_dir / "latest_llm_online.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in report["cases"]:
            writer.writerow({**row, **row.get("actual", {})})
    return latest


def main() -> int:
    parser = argparse.ArgumentParser(description="运行真实在线 LLM 能力测试并生成 JSON/CSV 报告")
    parser.add_argument("--confirm-online", action="store_true", help="确认会调用真实模型并产生 API 费用")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--case", action="append", dest="case_ids", help="只运行指定 case id，可重复")
    parser.add_argument(
        "--merge-existing", action="store_true",
        help="将指定 case 的新结果合并进已有完整报告，避免重跑已通过案例",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="不调用模型，只用 output-dir 中已有的 latest JSON 重建 JSON/CSV",
    )
    parser.add_argument(
        "--restore-report", type=Path,
        help="不调用模型，将指定的时间戳 JSON 恢复为 latest 并重建表格数据",
    )
    args = parser.parse_args()
    if args.restore_report:
        source = args.restore_report.resolve()
        if not source.exists():
            parser.error(f"待恢复报告不存在：{source}")
        report = json.loads(source.read_text(encoding="utf-8"))
        report = regrade_report(report, load_dataset(args.dataset.resolve()))
        latest = write_report(report, args.output_dir.resolve())
        print(json.dumps(report.get("summary", {}), ensure_ascii=False, indent=2))
        print(f"Restored JSON: {latest}")
        return 0
    if args.report_only:
        existing = args.output_dir.resolve() / "latest_llm_online.json"
        if not existing.exists():
            parser.error(f"没有可恢复的在线报告：{existing}")
        report = json.loads(existing.read_text(encoding="utf-8"))
        report = regrade_report(report, load_dataset(args.dataset.resolve()))
        latest = write_report(report, args.output_dir.resolve())
        print(json.dumps(report.get("summary", {}), ensure_ascii=False, indent=2))
        print(f"JSON: {latest}")
        print(f"CSV: {args.output_dir.resolve() / 'latest_llm_online.csv'}")
        # 恢复模式只负责重建报告；历史能力结果是否通过仍保留在 summary，
        # 不应把“存在失败用例”误报成“报告恢复失败”。
        return 0
    if not args.confirm_online:
        parser.error("必须显式提供 --confirm-online，防止误用 API 额度")
    if settings.OPENAI_API_KEY.strip().casefold() in PLACEHOLDER_KEYS:
        parser.error("OPENAI_API_KEY 未配置或仍为占位值")
    if not settings.RESEARCH_ANALYSIS_WITH_LLM:
        parser.error("RESEARCH_ANALYSIS_WITH_LLM 必须为 true")

    dataset = load_dataset(args.dataset.resolve())
    cases = materialize_cases(dataset)
    if args.case_ids:
        requested = set(args.case_ids)
        cases = [case for case in cases if case["id"] in requested]
        missing = requested - {case["id"] for case in cases}
        if missing:
            parser.error("未知 case id: " + ", ".join(sorted(missing)))
    results = [evaluate_case(case) for case in cases]
    if args.merge_existing:
        if not args.case_ids:
            parser.error("--merge-existing 必须与至少一个 --case 一起使用")
        existing_path = args.output_dir.resolve() / "latest_llm_online.json"
        if not existing_path.exists():
            parser.error(f"没有可合并的已有报告：{existing_path}")
        existing_report = json.loads(existing_path.read_text(encoding="utf-8"))
        if (
            existing_report.get("dataset_name") != dataset["dataset_name"]
            or existing_report.get("dataset_version") != dataset["version"]
        ):
            parser.error(
                "已有报告与当前数据集身份不同，禁止合并；请使用独立 output-dir"
            )
        if (
            existing_report.get("dataset_name") != dataset["dataset_name"]
            or existing_report.get("dataset_version") != dataset["version"]
        ):
            parser.error(
                "已有报告与当前数据集身份不同，禁止合并；请使用独立 output-dir"
            )
        results = merge_case_results(
            existing_report.get("cases", []), results
        )
    total_calls = sum(row.get("actual", {}).get("llm_calls", 0) for row in results)
    total_tokens = sum(row.get("actual", {}).get("tokens", 0) for row in results)
    passed = sum(row["passed"] for row in results)
    provider_failures = sum(row.get("failure_kind") == "provider" for row in results)
    capability_failures = sum(row.get("failure_kind") == "capability" for row in results)
    report = {
        "report_version": "1.0", "dataset_name": dataset["dataset_name"],
        "dataset_version": dataset["version"], "generated_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_commit(), "model": settings.MODEL_NAME,
        "base_url": settings.OPENAI_BASE_URL, "mode": "online_real_llm",
        "summary": {"case_count": len(results), "passed_count": passed,
                    "failed_count": len(results) - passed,
                    "provider_failure_count": provider_failures,
                    "capability_failure_count": capability_failures,
                    "pass_rate_pct": round(passed / len(results) * 100, 2) if results else 0,
                    "llm_call_count": total_calls, "token_usage": total_tokens,
                    "duration_seconds": round(sum(row["duration_seconds"] for row in results), 3)},
        "cases": results,
    }
    latest = write_report(report, args.output_dir.resolve())
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"JSON: {latest}")
    print(f"CSV: {args.output_dir.resolve() / 'latest_llm_online.csv'}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
