"""最终回答质量 A/B：相同冻结证据下比较直接生成与 PaperAgent 证据约束链。"""

from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.config import settings
from core.llm_usage import invoke_llm_with_usage
from nodes.answer_verify import answer_verify_node
from nodes.claim_evidence_validate import claim_evidence_validate_node
from nodes.generate import generate_node, get_llm
from nodes.research_citation_validate import research_citation_validate_node

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "eval_harness/datasets/answer_quality_ab_v1.json"
DEFAULT_OUTPUT = ROOT / "outputs/answer_quality_ab"
REFERENCE_RE = re.compile(r"\[(E-[A-Za-z0-9_-]+)\]")


def load_dataset(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    cases = data.get("cases", [])
    ids = [case.get("id") for case in cases]
    if not data.get("frozen") or not 15 <= len(cases) <= 20 or len(ids) != len(set(ids)):
        raise ValueError("回答质量评测集必须冻结、包含15至20个唯一案例")
    required = {"required_dimensions", "facts", "evidence", "forbidden_claims"}
    if any(not required.issubset(case) for case in cases):
        raise ValueError("每个案例必须包含人工维度、事实、证据和禁止声明")
    return data


def _units(answer: str) -> list[str]:
    return [part.strip() for part in re.split(r"[\n。！？]+", answer) if part.strip()]


def _contains_all(text: str, keywords: list[str]) -> bool:
    folded = text.casefold()
    return all(keyword.casefold() in folded for keyword in keywords)


def grade_answer(case: dict[str, Any], answer: str) -> dict[str, Any]:
    units = _units(answer)
    allowed_ids = {item["evidence_id"] for item in case["evidence"]}
    cited_ids = REFERENCE_RE.findall(answer)
    valid_ids = [item for item in cited_ids if item in allowed_ids]
    hallucinated_ids = sorted(set(cited_ids) - allowed_ids)

    dimension_rows = []
    for dimension in case["required_dimensions"]:
        matched = any(keyword.casefold() in answer.casefold() for keyword in dimension["keywords"])
        dimension_rows.append({"name": dimension["name"], "covered": matched})

    fact_rows = []
    for fact in case["facts"]:
        matches = [unit for unit in units if _contains_all(unit, fact["keywords"])]
        nearby = {item for unit in matches for item in REFERENCE_RE.findall(unit)}
        mentioned = bool(matches)
        grounded = bool(nearby & set(fact["allowed_evidence_ids"]))
        fact_rows.append({
            "label": fact["label"], "mentioned": mentioned, "grounded": grounded,
            "nearby_evidence_ids": sorted(nearby),
        })

    insufficiency_required = bool(case.get("insufficient_topics"))
    insufficiency_disclosed = (
        any(keyword.casefold() in answer.casefold() for keyword in case.get("insufficient_keywords", []))
        if insufficiency_required else True
    )
    forbidden_hits = [claim for claim in case["forbidden_claims"] if claim.casefold() in answer.casefold()]
    dimension_pct = round(sum(row["covered"] for row in dimension_rows) / len(dimension_rows) * 100, 2)
    fact_pct = round(sum(row["mentioned"] for row in fact_rows) / len(fact_rows) * 100, 2)
    grounded_pct = round(sum(row["grounded"] for row in fact_rows) / len(fact_rows) * 100, 2)
    citation_accuracy_pct = round(len(valid_ids) / len(cited_ids) * 100, 2) if cited_ids else 0.0
    traceability_pct = round(len(set(valid_ids)) / len(allowed_ids) * 100, 2) if allowed_ids else 100.0
    safe = not forbidden_hits and insufficiency_disclosed
    content_score = round(
        dimension_pct * 0.45 + fact_pct * 0.35 + (100.0 if safe else 0.0) * 0.20,
        2,
    )
    score = round(
        dimension_pct * 0.25 + fact_pct * 0.15 + grounded_pct * 0.25
        + citation_accuracy_pct * 0.15 + traceability_pct * 0.10 + (100.0 if safe else 0.0) * 0.10,
        2,
    )
    passed = bool(dimension_pct == 100 and grounded_pct == 100 and citation_accuracy_pct == 100 and safe)
    return {
        "passed": passed,
        "metrics": {
            "quality_score": score,
            "answer_content_score": content_score,
            "dimension_coverage_pct": dimension_pct,
            "key_fact_coverage_pct": fact_pct,
            "claim_evidence_support_pct": grounded_pct,
            "citation_accuracy_pct": citation_accuracy_pct,
            "evidence_traceability_pct": traceability_pct,
            "insufficiency_disclosed": insufficiency_disclosed,
            "insufficiency_required": insufficiency_required,
            "forbidden_claim_count": len(forbidden_hits),
            "hallucinated_citation_count": len(hallucinated_ids),
        },
        "dimension_results": dimension_rows,
        "fact_results": fact_rows,
        "forbidden_claim_hits": forbidden_hits,
        "hallucinated_evidence_ids": hallucinated_ids,
    }


def _documents(case: dict[str, Any]) -> list[dict[str, Any]]:
    return [{
        "title": item["title"], "source": item["source"], "content": item["snippet"],
        "pdf_url": item["locator"], "year": None,
    } for item in case["evidence"]]


def _state(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "query": case["query"], "task_type": "recommend", "task_level": "L3",
        "documents": _documents(case), "retrieval_outcome": "accepted", "llm_usage": [],
        "research_analysis": {"primary_skill": case["skill"]},
        "research_coverage": {"enabled": True, "status": "passed", "coverage_pct": 100.0,
                              "writer_allowed": True, "uncovered_claims": []},
        "evidence_store": {"enabled": True, "evidence": case["evidence"]},
        "answer_reflection_count": 0,
    }


def _baseline_prompt(case: dict[str, Any]) -> str:
    materials = "\n\n".join(
        f"材料 {index}：{item['title']}\n{item['snippet']}"
        for index, item in enumerate(case["evidence"], start=1)
    )
    return f"""请根据下面提供的论文材料回答用户问题，输出清晰的中文研究回答。

用户问题：{case['query']}

论文材料：
{materials}
"""


def _run_baseline(case: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    start = time.perf_counter()
    response, usage = invoke_llm_with_usage(
        llm=get_llm(), prompt=_baseline_prompt(case), node_name="answer_quality_baseline",
        model_name=settings.MODEL_NAME, prompt_version="direct_generation_v1",
    )
    return str(response.content), {
        "llm_call_count": 1, "failed_llm_call_count": 0,
        "token_usage": usage.get("total_tokens", 0), "duration_seconds": round(time.perf_counter() - start, 3),
    }


def _run_paper_agent(case: dict[str, Any]) -> tuple[str, dict[str, Any], dict[str, Any]]:
    start = time.perf_counter()
    state = _state(case)
    generated = generate_node(state)
    state.update(generated)
    citation = research_citation_validate_node(state)
    state.update(citation)
    claim = claim_evidence_validate_node(state)
    state.update(claim)
    verified = answer_verify_node(state)
    state.update(verified)
    duration = round(time.perf_counter() - start, 3)
    return str(state.get("answer", "")), {
        "llm_call_count": state.get("llm_call_count", 0),
        "failed_llm_call_count": state.get("llm_failed_call_count", 0),
        "token_usage": state.get("token_usage", 0), "duration_seconds": duration,
    }, {
        "citation_validation": state.get("citation_validation", {}),
        "claim_evidence_validation": state.get("claim_evidence_validation", {}),
        "answer_verification": state.get("answer_verification", {}),
    }


def _variant_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    count = len(rows)
    metric_names = [
        "quality_score", "answer_content_score", "dimension_coverage_pct", "key_fact_coverage_pct",
        "claim_evidence_support_pct", "citation_accuracy_pct", "evidence_traceability_pct",
    ]
    summary = {
        "case_count": count, "passed_count": sum(row["passed"] for row in rows),
        "pass_rate_pct": round(sum(row["passed"] for row in rows) / count * 100, 2),
        "forbidden_claim_count": sum(row["metrics"]["forbidden_claim_count"] for row in rows),
        "hallucinated_citation_count": sum(row["metrics"]["hallucinated_citation_count"] for row in rows),
        "llm_call_count": sum(row["usage"]["llm_call_count"] for row in rows),
        "failed_llm_call_count": sum(row["usage"]["failed_llm_call_count"] for row in rows),
        "token_usage": sum(row["usage"]["token_usage"] for row in rows),
        "average_tokens": round(sum(row["usage"]["token_usage"] for row in rows) / count, 2),
        "average_latency_seconds": round(statistics.mean(row["usage"]["duration_seconds"] for row in rows), 3),
    }
    insufficiency_rows = [row for row in rows if row["metrics"]["insufficiency_required"]]
    summary["insufficiency_case_count"] = len(insufficiency_rows)
    summary["insufficiency_disclosure_rate_pct"] = round(
        sum(row["metrics"]["insufficiency_disclosed"] for row in insufficiency_rows)
        / len(insufficiency_rows) * 100, 2
    ) if insufficiency_rows else 100.0
    for metric in metric_names:
        summary[metric] = round(statistics.mean(row["metrics"][metric] for row in rows), 2)
    latencies = sorted(row["usage"]["duration_seconds"] for row in rows)
    summary["p95_latency_seconds"] = round(latencies[min(len(latencies) - 1, int(len(latencies) * 0.95))], 3)
    return summary


def _comparison(baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    quality_metrics = [
        "pass_rate_pct", "quality_score", "answer_content_score", "dimension_coverage_pct", "key_fact_coverage_pct",
        "claim_evidence_support_pct", "citation_accuracy_pct", "evidence_traceability_pct",
        "insufficiency_disclosure_rate_pct",
    ]
    result = {metric + "_delta": round(candidate[metric] - baseline[metric], 2) for metric in quality_metrics}
    result["average_tokens_delta_pct"] = round(
        (candidate["average_tokens"] - baseline["average_tokens"]) / baseline["average_tokens"] * 100
        if baseline["average_tokens"] else 0.0, 2
    )
    result["p95_latency_delta_pct"] = round(
        (candidate["p95_latency_seconds"] - baseline["p95_latency_seconds"]) / baseline["p95_latency_seconds"] * 100
        if baseline["p95_latency_seconds"] else 0.0, 2
    )
    return result


def run_online(dataset: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for index, case in enumerate(dataset["cases"], start=1):
        print(f"[{index}/{len(dataset['cases'])}] {case['id']} baseline", flush=True)
        baseline_answer, baseline_usage = _run_baseline(case)
        print(f"[{index}/{len(dataset['cases'])}] {case['id']} paper_agent", flush=True)
        candidate_answer, candidate_usage, validators = _run_paper_agent(case)
        rows.append({
            "id": case["id"], "category": case["category"], "query": case["query"],
            "baseline": {"answer": baseline_answer, "usage": baseline_usage,
                         **grade_answer(case, baseline_answer)},
            "paper_agent": {"answer": candidate_answer, "usage": candidate_usage,
                            "validators": validators, **grade_answer(case, candidate_answer)},
        })
    baseline = _variant_summary([{**row["baseline"], "id": row["id"]} for row in rows])
    candidate = _variant_summary([{**row["paper_agent"], "id": row["id"]} for row in rows])
    return {
        "report_version": "1.0", "dataset_name": dataset["dataset_name"],
        "dataset_version": dataset["dataset_version"], "mode": "online_real_llm_ab",
        "model": settings.MODEL_NAME, "generated_at": datetime.now(timezone.utc).isoformat(),
        "annotation": dataset["annotation"], "baseline": baseline, "paper_agent": candidate,
        "comparison": _comparison(baseline, candidate), "cases": rows,
    }


def rerun_paper_agent_case(
    dataset: dict[str, Any], existing: dict[str, Any], case_id: str
) -> dict[str, Any]:
    """只重跑发生供应商失败的 PaperAgent 侧，保留其他已付费原始回答。"""
    case_map = {case["id"]: case for case in dataset["cases"]}
    if case_id not in case_map:
        raise ValueError(f"未知 case_id: {case_id}")
    rows = []
    for row in existing["cases"]:
        if row["id"] != case_id:
            rows.append(row)
            continue
        case = case_map[case_id]
        answer, usage, validators = _run_paper_agent(case)
        rows.append({**row, "paper_agent": {
            "answer": answer, "usage": usage, "validators": validators,
            **grade_answer(case, answer),
        }})
    baseline = _variant_summary([row["baseline"] for row in rows])
    candidate = _variant_summary([row["paper_agent"] for row in rows])
    return {
        **existing, "mode": "online_real_llm_ab_targeted_merge",
        "merged_at": datetime.now(timezone.utc).isoformat(),
        "baseline": baseline, "paper_agent": candidate,
        "comparison": _comparison(baseline, candidate), "cases": rows,
    }


def regrade(dataset: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    case_map = {case["id"]: case for case in dataset["cases"]}
    rows = []
    for row in report["cases"]:
        case = case_map[row["id"]]
        baseline = {**row["baseline"], **grade_answer(case, row["baseline"]["answer"])}
        candidate = {**row["paper_agent"], **grade_answer(case, row["paper_agent"]["answer"])}
        rows.append({**row, "baseline": baseline, "paper_agent": candidate})
    baseline_summary = _variant_summary([row["baseline"] for row in rows])
    candidate_summary = _variant_summary([row["paper_agent"] for row in rows])
    return {**report, "mode": "online_real_llm_ab_regraded", "regraded_at": datetime.now(timezone.utc).isoformat(),
            "baseline": baseline_summary, "paper_agent": candidate_summary,
            "comparison": _comparison(baseline_summary, candidate_summary), "cases": rows}


def write_report(report: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "latest_answer_quality_ab.json"
    csv_path = output_dir / "latest_answer_quality_ab.csv"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    fields = ["id", "category", "variant", "passed", "quality_score", "answer_content_score", "dimension_coverage_pct",
              "key_fact_coverage_pct", "claim_evidence_support_pct", "citation_accuracy_pct",
              "evidence_traceability_pct", "insufficiency_disclosed", "insufficiency_required", "forbidden_claim_count",
              "hallucinated_citation_count",
              "llm_calls", "tokens", "duration_seconds", "query", "answer"]
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in report["cases"]:
            for variant in ("baseline", "paper_agent"):
                item = row[variant]
                writer.writerow({
                    "id": row["id"], "category": row["category"], "variant": variant,
                    "passed": item["passed"], **item["metrics"],
                    "llm_calls": item["usage"]["llm_call_count"], "tokens": item["usage"]["token_usage"],
                    "duration_seconds": item["usage"]["duration_seconds"], "query": row["query"],
                    "answer": item["answer"],
                })
    return json_path, csv_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--confirm-online", action="store_true")
    parser.add_argument("--input-report", type=Path)
    parser.add_argument("--merge-report", type=Path)
    parser.add_argument("--rerun-paper-agent-case")
    args = parser.parse_args()
    dataset = load_dataset(args.dataset.resolve())
    if args.rerun_paper_agent_case:
        if not args.confirm_online or not args.merge_report:
            raise SystemExit("定向重跑需要 --confirm-online 和 --merge-report。")
        existing = json.loads(args.merge_report.resolve().read_text(encoding="utf-8"))
        report = rerun_paper_agent_case(dataset, existing, args.rerun_paper_agent_case)
    elif args.input_report:
        report = regrade(dataset, json.loads(args.input_report.resolve().read_text(encoding="utf-8")))
    elif args.confirm_online:
        report = run_online(dataset)
    else:
        raise SystemExit("该评测会调用真实模型；请显式添加 --confirm-online，或使用 --input-report 离线重判。")
    paths = write_report(report, args.output_dir.resolve())
    print(json.dumps({"baseline": report["baseline"], "paper_agent": report["paper_agent"],
                      "comparison": report["comparison"]}, ensure_ascii=False, indent=2))
    print(f"JSON: {paths[0]}\nCSV: {paths[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
