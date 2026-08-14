"""小型研究报告引用与结构评测；默认只验证人工参考报告。"""

from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nodes.generate import generate_node
from nodes.research_citation_validate import research_citation_validate_node

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "eval_harness/datasets/research_report_v1.json"
DEFAULT_OUTPUT = ROOT / "outputs/research_report_eval"
REFERENCE_RE = re.compile(r"\[(E-[A-Za-z0-9_-]+)\]")
SECTION_ALIASES = {
    "研究范围": ["研究范围", "scope"],
    "方法比较": ["方法比较", "方法对比", "method comparison", "method_comparison"],
    "研究空白": ["研究空白", "research gaps", "research_gaps"],
    "证据索引": ["证据索引", "evidence index", "evidence reference"],
    "贡献": ["贡献", "claimed contributions", "claimed_contributions"],
    "优势": ["优势", "strengths"],
    "局限": ["局限", "weaknesses", "limitations"],
}
CLAIM_KEYWORD_ALIASES = {
    "比较": ("比较", "对比", "相较"),
    "差异": ("差异", "不同", "区别"),
}


def _claim_keyword_present(keyword: str, text: str) -> bool:
    return any(
        candidate.casefold() in text.casefold()
        for candidate in CLAIM_KEYWORD_ALIASES.get(keyword, (keyword,))
    )


def load_dataset(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    ids = [case["id"] for case in data.get("cases", [])]
    if not data.get("frozen") or len(ids) != 4 or len(ids) != len(set(ids)):
        raise ValueError("研究报告评测集必须冻结、包含4个唯一案例")
    return data


def grade_report(case: dict[str, Any], answer: str) -> dict[str, Any]:
    allowed = {item["evidence_id"] for item in case["evidence"]}
    cited = REFERENCE_RE.findall(answer)
    valid = [item for item in cited if item in allowed]
    hallucinated = sorted(set(cited) - allowed)
    # 声明与引用必须出现在同一行或同一句，防止整节中上一条 bullet 的
    # 引用被错误借给下一条没有证据的综合判断。
    citation_attached = re.sub(r"[。！？]\s*(?=\[E-)", " ", answer)
    units = [part.strip() for part in re.split(r"[\n。！？]+", citation_attached) if part.strip()]
    claim_rows = []
    for claim in case["claims"]:
        matching = [p for p in units if any(_claim_keyword_present(k, p) for k in claim["keywords"])]
        nearby_ids = {item for p in matching for item in REFERENCE_RE.findall(p)}
        supported = bool(nearby_ids & set(claim["allowed_evidence_ids"]))
        claim_rows.append({"label": claim["label"], "supported": supported,
                           "nearby_evidence_ids": sorted(nearby_ids)})
    answer_folded = answer.casefold()
    section_hits = [
        section for section in case["required_sections"]
        if any(alias.casefold() in answer_folded for alias in SECTION_ALIASES.get(section, [section]))
    ]
    citation_existence_pct = round(len(valid) / len(cited) * 100, 2) if cited else 0.0
    claim_coverage_pct = round(sum(row["supported"] for row in claim_rows) / len(claim_rows) * 100, 2)
    structure_pct = round(len(section_hits) / len(case["required_sections"]) * 100, 2)
    passed = citation_existence_pct == 100 and not hallucinated and claim_coverage_pct == 100 and structure_pct == 100
    return {
        "passed": passed,
        "metrics": {
            "citation_count": len(cited), "valid_citation_count": len(valid),
            "citation_existence_pct": citation_existence_pct,
            "hallucinated_citation_count": len(hallucinated),
            "claim_coverage_pct": claim_coverage_pct,
            "structure_completeness_pct": structure_pct,
        },
        "hallucinated_evidence_ids": hallucinated,
        "claim_results": claim_rows,
        "section_hits": section_hits,
    }


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    metrics = [row["metrics"] for row in rows]
    return {
        "case_count": len(rows), "passed_count": sum(row["passed"] for row in rows),
        "pass_rate_pct": round(sum(row["passed"] for row in rows) / len(rows) * 100, 2),
        "citation_existence_pct": round(sum(m["citation_existence_pct"] for m in metrics) / len(metrics), 2),
        "claim_coverage_pct": round(sum(m["claim_coverage_pct"] for m in metrics) / len(metrics), 2),
        "structure_completeness_pct": round(sum(m["structure_completeness_pct"] for m in metrics) / len(metrics), 2),
        "hallucinated_citation_count": sum(m["hallucinated_citation_count"] for m in metrics),
        "llm_call_count": sum(row["usage"]["llm_call_count"] for row in rows),
        "failed_llm_call_count": sum(row["usage"]["llm_failed_call_count"] for row in rows),
        "token_usage": sum(row["usage"]["token_usage"] for row in rows),
    }


def run(dataset: dict[str, Any], online: bool = False, case_ids: set[str] | None = None) -> dict[str, Any]:
    rows = []
    for case in dataset["cases"]:
        if case_ids and case["id"] not in case_ids:
            continue
        if online:
            documents = [{"title": e["title"], "source": e["source"],
                          "content": e["snippet"], "pdf_url": e["locator"]} for e in case["evidence"]]
            state = {
                "query": case["query"], "task_type": "recommend", "task_level": "L3",
                "documents": documents, "retrieval_outcome": "accepted", "llm_usage": [],
                "research_analysis": {"primary_skill": case["skill"]},
                "research_coverage": {"enabled": True, "status": "passed", "coverage_pct": 100,
                                      "writer_allowed": True, "uncovered_claims": []},
                "evidence_store": {"enabled": True, "evidence": case["evidence"]},
            }
            result = generate_node(state)
            answer = result.get("answer", "")
            usage = {key: result.get(key, 0) for key in ("llm_call_count", "token_usage", "llm_failed_call_count")}
            citation_validation = research_citation_validate_node({**state, **result})["citation_validation"]
        else:
            answer, usage = case["reference_report"], {"llm_call_count": 0, "token_usage": 0, "llm_failed_call_count": 0}
            citation_validation = research_citation_validate_node({
                "task_level": "L3", "answer": answer,
                "research_coverage": {"enabled": True},
                "research_analysis": {"primary_skill": case["skill"]},
                "evidence_store": {"evidence": case["evidence"]},
            })["citation_validation"]
        rows.append({"id": case["id"], "query": case["query"], "answer": answer,
                     "human_annotation": "claims.allowed_evidence_ids由人工阅读冻结证据后标注",
                     "usage": usage, "citation_validation": citation_validation,
                     **grade_report(case, answer)})
    metrics = [row["metrics"] for row in rows]
    return {
        "dataset_name": dataset["dataset_name"], "dataset_version": dataset["dataset_version"],
        "mode": "online_llm" if online else "reference_harness_validation",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": _summary(rows), "cases": rows,
    }


def regrade_existing(dataset: dict[str, Any], existing: dict[str, Any]) -> dict[str, Any]:
    """复用已经付费的模型原文重新判分，不发起任何模型调用。"""
    answers = {row["id"]: row for row in existing.get("cases", [])}
    rows = []
    for case in dataset["cases"]:
        prior = answers[case["id"]]
        citation_validation = research_citation_validate_node({
            "task_level": "L3", "answer": str(prior.get("answer", "")),
            "research_coverage": {"enabled": True},
            "research_analysis": {"primary_skill": case["skill"]},
            "evidence_store": {"evidence": case["evidence"]},
        })["citation_validation"]
        rows.append({
            **prior,
            "citation_validation": citation_validation,
            **grade_report(case, str(prior.get("answer", ""))),
        })
    metrics = [row["metrics"] for row in rows]
    return {
        **existing,
        "mode": "online_llm_regraded",
        "regraded_at": datetime.now(timezone.utc).isoformat(),
        "summary": _summary(rows), "cases": rows,
    }


def merge_results(existing: dict[str, Any], rerun: dict[str, Any]) -> dict[str, Any]:
    """按case合并定向重跑，未重跑案例保持原文和用量不变。"""
    replacements = {row["id"]: row for row in rerun["cases"]}
    rows = [replacements.get(row["id"], row) for row in existing["cases"]]
    known = {row["id"] for row in rows}
    rows.extend(row for row in rerun["cases"] if row["id"] not in known)
    return {**existing, "mode": "online_llm_merged", "merged_at": datetime.now(timezone.utc).isoformat(),
            "summary": _summary(rows), "cases": rows}


def write_report(report: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path, csv_path = output_dir / "latest_research_report_eval.json", output_dir / "latest_research_report_eval.csv"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["id", "passed", "citation_existence_pct", "claim_coverage_pct", "structure_completeness_pct", "hallucinated_citation_count", "llm_calls", "tokens", "query"])
        writer.writeheader()
        for row in report["cases"]:
            metrics = row["metrics"]
            writer.writerow({
                "id": row["id"], "passed": row["passed"],
                "citation_existence_pct": metrics["citation_existence_pct"],
                "claim_coverage_pct": metrics["claim_coverage_pct"],
                "structure_completeness_pct": metrics["structure_completeness_pct"],
                "hallucinated_citation_count": metrics["hallucinated_citation_count"],
                "llm_calls": row["usage"]["llm_call_count"],
                "tokens": row["usage"]["token_usage"], "query": row["query"],
            })
    return json_path, csv_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--confirm-online", action="store_true")
    parser.add_argument("--input-report", type=Path)
    parser.add_argument("--case-id", action="append", default=[])
    parser.add_argument("--merge-report", type=Path)
    args = parser.parse_args()
    dataset = load_dataset(args.dataset.resolve())
    if args.input_report:
        existing = json.loads(args.input_report.resolve().read_text(encoding="utf-8"))
        report = regrade_existing(dataset, existing)
    else:
        report = run(dataset, online=args.confirm_online, case_ids=set(args.case_id) or None)
        if args.merge_report:
            existing = json.loads(args.merge_report.resolve().read_text(encoding="utf-8"))
            report = merge_results(existing, report)
    paths = write_report(report, args.output_dir.resolve())
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"JSON: {paths[0]}\nCSV: {paths[1]}")
    return 0 if report["summary"]["passed_count"] == report["summary"]["case_count"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
