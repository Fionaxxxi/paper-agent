"""Research Agent 的请求级、可追溯 Evidence Store。"""

from __future__ import annotations

import hashlib
import re
from typing import Any


def _locator(document: dict[str, Any]) -> str:
    if document.get("chunk_id"):
        page = f" page={document.get('page')}" if document.get("page") else ""
        return f"chunk:{document['chunk_id']}{page}"
    if document.get("doi"):
        return f"doi:{document['doi']}"
    return str(document.get("pdf_url") or document.get("url") or document.get("entry_id") or "unlocated")


def _evidence_id(document: dict[str, Any]) -> str:
    identity = "|".join((
        str(document.get("title") or ""),
        str(document.get("source") or ""),
        _locator(document),
    ))
    return "E-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:12]


def _terms(text: str) -> set[str]:
    return {
        token.casefold() for token in re.findall(r"[A-Za-z][A-Za-z0-9-]{2,}|[\u4e00-\u9fff]{2,}", text)
    }


def build_evidence_store(
    schedule: dict[str, Any], documents: list[dict[str, Any]]
) -> dict[str, Any]:
    retrieval_tasks = [
        task for wave in schedule.get("waves", []) for task in wave["tasks"]
        if task.get("task_kind") == "retrieval"
    ]
    synthesis_tasks = [
        task for wave in schedule.get("waves", []) for task in wave["tasks"]
        if task.get("task_kind") == "synthesis"
    ]
    records: dict[str, dict[str, Any]] = {}
    task_evidence: dict[str, list[str]] = {task["task_id"]: [] for task in retrieval_tasks}
    for document in documents:
        evidence_id = _evidence_id(document)
        record = records.setdefault(evidence_id, {
            "evidence_id": evidence_id,
            "title": str(document.get("title") or "未命名论文"),
            "source": str(document.get("source") or "unknown"),
            "evidence_type": str(document.get("evidence_type") or "paper"),
            "locator": _locator(document),
            "year": document.get("year"),
            "snippet": str(document.get("content") or "")[:600],
            "score": document.get("retrieval_score", document.get("relevance_score", 0.0)),
            "task_ids": [],
        })
        document_terms = _terms(record["title"] + " " + record["snippet"])
        scored = []
        for task in retrieval_tasks:
            overlap = len(_terms(task.get("query", "") + " " + task.get("objective", "")) & document_terms)
            scored.append((overlap, task["task_id"]))
        matched = [task_id for overlap, task_id in scored if overlap > 0]
        if not matched and retrieval_tasks:
            matched = [retrieval_tasks[len(records) % len(retrieval_tasks)]["task_id"]]
        for task_id in matched:
            if evidence_id not in task_evidence[task_id]:
                task_evidence[task_id].append(evidence_id)
            if task_id not in record["task_ids"]:
                record["task_ids"].append(task_id)

    claim_inputs = []
    for task in synthesis_tasks:
        evidence_ids = list(dict.fromkeys(
            evidence_id
            for dependency in task.get("depends_on", [])
            for evidence_id in task_evidence.get(dependency, [])
        ))
        missing_dependencies = [
            dependency for dependency in task.get("depends_on", [])
            if not task_evidence.get(dependency)
        ]
        claim_inputs.append({
            "task_id": task["task_id"],
            "claim": task.get("objective", ""),
            "depends_on": task.get("depends_on", []),
            "evidence_ids": evidence_ids,
            "missing_dependency_task_ids": missing_dependencies,
            "coverage_ready": bool(evidence_ids) and not missing_dependencies,
        })
    return {
        "enabled": bool(schedule.get("enabled")),
        "evidence": list(records.values()),
        "task_evidence": task_evidence,
        "claim_evidence_inputs": claim_inputs,
        "evidence_count": len(records),
        "status": "collected" if records else "empty",
    }
