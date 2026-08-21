from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from evolution.models import FailureDataset, FailureRecord


FAILURE_MODULE_MAP = {
    "intent": "intent_router",
    "clarification": "clarification",
    "plan": "query_planning",
    "query": "query_rewrite",
    "retrieval": "retrieval",
    "coverage": "research_coverage",
    "tool": "tool_execution",
    "citation": "citation_validation",
    "claim": "claim_evidence_validation",
    "grounding": "pdf_grounding",
    "answer": "answer_verification",
    "memory": "memory",
    "latency": "performance",
    "token": "cost",
}


def _load(path: Path) -> Any:
    if path.suffix.lower() == ".jsonl":
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return json.loads(path.read_text(encoding="utf-8"))


def _rows(payload: Any) -> Iterable[dict[str, Any]]:
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                yield item
        return
    if not isinstance(payload, dict):
        return
    for key in ("cases", "rows", "results", "records"):
        value = payload.get(key)
        if isinstance(value, list):
            yield from (item for item in value if isinstance(item, dict))
    for key in ("profiles", "variants"):
        value = payload.get(key)
        values = value.values() if isinstance(value, dict) else value if isinstance(value, list) else []
        for item in values:
            if isinstance(item, dict):
                yield from _rows(item)


def _failure_types(row: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for key in ("failure_types", "failures", "errors"):
        value = row.get(key)
        if isinstance(value, list):
            values.extend(str(item) for item in value if item)
        elif isinstance(value, str) and value:
            values.append(value)
    if row.get("failure_type"):
        values.append(str(row["failure_type"]))
    checks = row.get("checks")
    if isinstance(checks, dict):
        values.extend(str(name) for name, passed in checks.items() if passed is False)
    if not values and row.get("passed") is False:
        values.append("unspecified_capability_failure")
    return list(dict.fromkeys(values))


def _module(failure_type: str, row: dict[str, Any]) -> str:
    explicit = row.get("module") or row.get("node")
    if explicit:
        return str(explicit)
    lowered = failure_type.casefold()
    for marker, module in FAILURE_MODULE_MAP.items():
        if marker in lowered:
            return module
    return "unknown"


def _severity(failure_type: str, row: dict[str, Any]) -> str:
    if row.get("severity") in {"low", "medium", "high", "critical"}:
        return str(row["severity"])
    lowered = failure_type.casefold()
    if any(item in lowered for item in ("security", "permission", "private", "contradict")):
        return "critical"
    if any(item in lowered for item in ("citation", "claim", "grounding", "coverage")):
        return "high"
    return "medium"


def build_failure_dataset(paths: list[Path]) -> FailureDataset:
    records: list[FailureRecord] = []
    seen: set[tuple[str, str]] = set()
    for path in paths:
        payload = _load(path)
        for index, row in enumerate(_rows(payload), start=1):
            case_id = str(row.get("case_id") or row.get("id") or f"{path.stem}-{index}")
            for failure_type in _failure_types(row):
                key = (case_id, failure_type)
                if key in seen:
                    continue
                seen.add(key)
                records.append(FailureRecord(
                    case_id=case_id,
                    trace_id=str(row.get("trace_id") or ""),
                    module=_module(failure_type, row),
                    failure_type=failure_type,
                    severity=_severity(failure_type, row),
                    query=str(row.get("query") or row.get("input") or ""),
                    source=path.name,
                    evidence={
                        key: row[key] for key in ("expected", "actual", "checks", "score") if key in row
                    },
                ))
    by_module = Counter(record.module for record in records)
    by_type = Counter(record.failure_type for record in records)
    return FailureDataset(
        source_files=[str(path) for path in paths],
        records=records,
        summary={
            "failure_count": len(records),
            "case_count": len({record.case_id for record in records}),
            "critical_count": sum(record.severity == "critical" for record in records),
            "by_module": dict(sorted(by_module.items())),
            "by_failure_type": dict(sorted(by_type.items())),
        },
    )
