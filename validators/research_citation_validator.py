"""Research Writer 输出的确定性引用与证据边界检查。"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field


REFERENCE_RE = re.compile(r"\[(E-[A-Za-z0-9_-]+)\]")
SYNTHESIS_MARKERS = ("综合判断", "综合分析", "综合来看", "综合而言")
SYNTHESIS_SUGGESTION_MARKERS = ("建议", "探索", "未来", "可进一步", "若", "需进一步")
CRITIQUE_OVERREACH_PATTERNS = (
    re.compile(r"(?:该|此)?(?:论文|贡献|方法).{0,24}(?:停留在|无法通过|不具备|没有实验|缺乏实验)"),
    re.compile(r"无法通过.{0,16}(?:审查|评审)"),
)


class CitationValidation(BaseModel):
    enabled: bool = False
    passed: bool = True
    status: str = "not_applicable"
    cited_evidence_ids: list[str] = Field(default_factory=list)
    invalid_evidence_ids: list[str] = Field(default_factory=list)
    uncited_synthesis_lines: list[str] = Field(default_factory=list)
    critique_overreach_lines: list[str] = Field(default_factory=list)
    evidence_index_present: bool = False
    failure_types: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)


def validate_research_citations(state: dict[str, Any]) -> CitationValidation:
    if state.get("task_level") != "L3" or not state.get("research_coverage", {}).get("enabled"):
        return CitationValidation()

    answer = str(state.get("answer") or "")
    allowed = {
        str(item.get("evidence_id"))
        for item in state.get("evidence_store", {}).get("evidence", [])
        if item.get("evidence_id")
    }
    cited = list(dict.fromkeys(REFERENCE_RE.findall(answer)))
    invalid = sorted(set(cited) - allowed)
    lines = [line.strip() for line in answer.splitlines() if line.strip()]
    uncited_synthesis = []
    for line in lines:
        normalized = re.sub(r"^[\-*>#\s]+", "", line)
        normalized = re.sub(r"^[\[【*]+", "", normalized)
        starts_as_synthesis = any(
            normalized.startswith(marker) for marker in SYNTHESIS_MARKERS
        )
        is_suggestion = any(marker in normalized[:80] for marker in SYNTHESIS_SUGGESTION_MARKERS)
        is_meta = "标记为" in normalized or "占比" in normalized
        is_heading = (
            normalized.rstrip("*】]：: ") in SYNTHESIS_MARKERS
            or line.rstrip().endswith(("：", ":"))
        )
        if (
            starts_as_synthesis and not is_suggestion and not is_meta and not is_heading
            and not (set(REFERENCE_RE.findall(line)) & allowed)
        ):
            uncited_synthesis.append(line[:300])
    primary_skill = state.get("research_analysis", {}).get("primary_skill", "")
    critique_overreach = []
    if primary_skill == "paper_critique":
        critique_overreach = [
            line[:300] for line in lines
            if not any(prefix in line for prefix in ("当前材料", "提供的材料", "现有材料", "输入材料"))
            and any(pattern.search(line) for pattern in CRITIQUE_OVERREACH_PATTERNS)
        ]
    index_present = "证据索引" in answer or "evidence index" in answer.casefold()
    failures: list[str] = []
    issues: list[str] = []
    if not cited:
        failures.append("missing_research_citations")
        issues.append("研究报告没有使用任何稳定 Evidence ID。")
    if invalid:
        failures.append("invalid_evidence_id")
        issues.append(f"报告引用了 Evidence Store 中不存在的 ID：{', '.join(invalid)}")
    if uncited_synthesis:
        failures.append("uncited_synthesis_claim")
        issues.append("综合判断缺少同一行的 Evidence ID。")
    if critique_overreach:
        failures.append("critique_evidence_overreach")
        issues.append("批判报告把输入材料缺失推断成论文或贡献本身的缺陷。")
    if not index_present:
        failures.append("missing_evidence_index")
        issues.append("研究报告缺少证据索引。")
    return CitationValidation(
        enabled=True, passed=not failures,
        status="passed" if not failures else "failed",
        cited_evidence_ids=cited, invalid_evidence_ids=invalid,
        uncited_synthesis_lines=uncited_synthesis,
        critique_overreach_lines=critique_overreach,
        evidence_index_present=index_present,
        failure_types=failures, issues=issues,
    )
