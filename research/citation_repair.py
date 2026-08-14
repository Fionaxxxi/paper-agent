"""对可唯一定位论文标题的漏引综合判断执行零LLM安全补全。"""

from __future__ import annotations

import re
from typing import Any

from validators.research_citation_validator import validate_research_citations


def _title_mentioned(title: str, line: str) -> bool:
    if not title.strip():
        return False
    escaped = re.escape(title.strip())
    if title.isascii():
        return bool(re.search(rf"(?<![A-Za-z0-9]){escaped}(?![A-Za-z0-9])", line, re.I))
    return title.casefold() in line.casefold()


def repair_uncited_synthesis(state: dict[str, Any]) -> dict[str, Any]:
    validation = state.get("citation_validation") or validate_research_citations(state).model_dump(mode="python")
    failures = set(validation.get("failure_types", []))
    if failures != {"uncited_synthesis_claim"}:
        return {"status": "not_repairable", "answer": state.get("answer", ""),
                "repaired_line_count": 0, "added_evidence_ids": []}

    evidence_by_title: dict[str, list[str]] = {}
    for item in state.get("evidence_store", {}).get("evidence", []):
        title, evidence_id = str(item.get("title") or ""), str(item.get("evidence_id") or "")
        if title and evidence_id:
            evidence_by_title.setdefault(title, []).append(evidence_id)

    targets = set(validation.get("uncited_synthesis_lines", []))
    repaired_lines, added, count = [], [], 0
    for line in str(state.get("answer") or "").splitlines():
        if line.strip() not in targets:
            repaired_lines.append(line)
            continue
        matched_ids = []
        ambiguous = False
        for title, evidence_ids in evidence_by_title.items():
            if _title_mentioned(title, line):
                if len(evidence_ids) != 1:
                    ambiguous = True
                    break
                matched_ids.append(evidence_ids[0])
        matched_ids = list(dict.fromkeys(matched_ids))
        if ambiguous or not matched_ids:
            repaired_lines.append(line)
            continue
        repaired_lines.append(f"{line} {' '.join(f'[{item}]' for item in matched_ids)}")
        added.extend(matched_ids)
        count += 1

    answer = "\n".join(repaired_lines)
    repaired_state = {**state, "answer": answer}
    after = validate_research_citations(repaired_state).model_dump(mode="python")
    return {
        "status": "repaired" if count and after.get("passed") else "partially_repaired" if count else "no_unique_match",
        "answer": answer, "repaired_line_count": count,
        "added_evidence_ids": list(dict.fromkeys(added)),
        "validation_after": after,
    }
