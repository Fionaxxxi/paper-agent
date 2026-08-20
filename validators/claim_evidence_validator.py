"""逐声明检查 Evidence ID 与引用片段是否具备最低语义支持。"""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field

from validators.research_citation_validator import REFERENCE_RE


class ClaimCheck(BaseModel):
    claim: str
    evidence_ids: list[str] = Field(default_factory=list)
    matched_evidence_ids: list[str] = Field(default_factory=list)
    status: Literal["supported", "partial", "contradicted", "insufficient"]
    reason: str


class ClaimEvidenceValidation(BaseModel):
    enabled: bool = False
    passed: bool = True
    status: str = "not_applicable"
    claim_count: int = 0
    supported_count: int = 0
    partial_count: int = 0
    contradicted_count: int = 0
    insufficient_count: int = 0
    support_rate_pct: float = 0.0
    claims: list[ClaimCheck] = Field(default_factory=list)
    failure_types: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)


def _terms(text: str) -> set[str]:
    lowered = text.casefold()
    english = set(re.findall(r"[a-z][a-z0-9-]{2,}", lowered))
    chinese_runs = re.findall(r"[\u4e00-\u9fff]{2,}", lowered)
    chinese = {
        run[index:index + 2]
        for run in chinese_runs
        for index in range(max(1, len(run) - 1))
    }
    return english | chinese


def _claim_lines(answer: str) -> list[str]:
    claims = []
    in_index = False
    for raw in answer.splitlines():
        line = raw.strip()
        normalized = re.sub(r"^[#>*\-\d.、\s]+", "", line).strip()
        if "证据索引" in normalized or "evidence index" in normalized.casefold():
            in_index = True
            continue
        if in_index or not normalized or len(normalized) < 8:
            continue
        if line.startswith("#") or normalized.endswith(("：", ":")):
            continue
        if REFERENCE_RE.search(normalized):
            claims.append(normalized[:500])
    return claims


def validate_claim_evidence(state: dict[str, Any]) -> ClaimEvidenceValidation:
    store = state.get("evidence_store", {})
    if state.get("task_level") != "L3" or not store.get("enabled"):
        return ClaimEvidenceValidation()

    evidence = {
        str(item.get("evidence_id")): item
        for item in store.get("evidence", [])
        if item.get("evidence_id")
    }
    checks: list[ClaimCheck] = []
    for claim in _claim_lines(str(state.get("answer") or "")):
        cited = list(dict.fromkeys(REFERENCE_RE.findall(claim)))
        claim_terms = _terms(REFERENCE_RE.sub("", claim))
        matched = []
        contradicted = []
        for evidence_id in cited:
            item = evidence.get(evidence_id)
            if not item:
                continue
            evidence_text = f"{item.get('title', '')} {item.get('snippet', '')}"
            if claim_terms & _terms(evidence_text):
                matched.append(evidence_id)
                lowered = evidence_text.casefold()
                if any(marker in lowered for marker in (
                    "contradicts this claim", "does not support this claim",
                    "与该结论相反", "不支持该结论",
                )):
                    contradicted.append(evidence_id)
        if contradicted:
            status, reason = "contradicted", "引用证据明确包含与该声明冲突的标记。"
        elif not matched:
            status, reason = "insufficient", "没有有效引用片段与声明形成最低词项对应。"
        elif len(matched) < len(cited):
            status, reason = "partial", "只有部分引用证据与声明形成对应。"
        else:
            status, reason = "supported", "所有有效引用均与声明形成最低词项对应。"
        checks.append(ClaimCheck(
            claim=REFERENCE_RE.sub("", claim).strip(), evidence_ids=cited,
            matched_evidence_ids=matched, status=status, reason=reason,
        ))

    counts = {status: sum(check.status == status for check in checks) for status in (
        "supported", "partial", "contradicted", "insufficient"
    )}
    blocking = counts["contradicted"] + counts["insufficient"]
    failures = []
    issues = []
    if not checks:
        failures.append("claim_evidence_missing_claims")
        issues.append("研究报告没有可验证的带 Evidence ID 声明。")
    if counts["contradicted"]:
        failures.append("claim_evidence_contradicted")
        issues.append(f"{counts['contradicted']} 条声明与引用证据冲突。")
    if counts["insufficient"]:
        failures.append("claim_evidence_insufficient")
        issues.append(f"{counts['insufficient']} 条声明缺少最低证据支持。")
    support_rate = round(counts["supported"] / len(checks) * 100, 2) if checks else 0.0
    status = "passed" if checks and not blocking and not counts["partial"] else (
        "partial" if checks and not blocking else "failed"
    )
    return ClaimEvidenceValidation(
        enabled=True, passed=bool(checks) and not blocking, status=status,
        claim_count=len(checks), supported_count=counts["supported"],
        partial_count=counts["partial"], contradicted_count=counts["contradicted"],
        insufficient_count=counts["insufficient"], support_rate_pct=support_rate,
        claims=checks, failure_types=failures, issues=issues,
    )
