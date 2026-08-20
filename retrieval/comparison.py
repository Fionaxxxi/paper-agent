"""比较任务的实体保留与双边证据覆盖检查。"""

from __future__ import annotations

from typing import Any, Iterable

ENTITY_ALIASES = {
    "GraphRAG": ("graphrag", "graph rag", "from local to global"),
    "LightRAG": ("lightrag", "light rag", "simple and fast retrieval-augmented generation"),
}


def comparison_targets(query: str, task_type: str = "") -> list[str]:
    normalized = str(query).casefold()
    is_comparison = task_type == "compare" or any(
        signal in normalized
        for signal in ("比较", "对比", "区别", "差异", " vs ", " versus ", "compare")
    )
    if not is_comparison:
        return []
    return [name for name, aliases in ENTITY_ALIASES.items() if any(alias in normalized for alias in aliases)]


def document_entity(document: dict[str, Any], targets: Iterable[str]) -> str:
    text = f"{document.get('title', '')} {document.get('content', '')}".casefold()
    for target in targets:
        aliases = ENTITY_ALIASES.get(target, (target.casefold(),))
        if any(alias in text for alias in aliases):
            return target
    return ""


def comparison_coverage(documents: list[dict[str, Any]], targets: list[str]) -> dict[str, Any]:
    covered: list[str] = []
    for document in documents:
        entity = document_entity(document, targets)
        if entity and entity not in covered:
            covered.append(entity)
    missing = [target for target in targets if target not in covered]
    return {
        "enabled": len(targets) >= 2,
        "expected_entities": targets,
        "covered_entities": covered,
        "missing_entities": missing,
        "coverage_pct": round(len(covered) / len(targets) * 100, 2) if targets else 0.0,
        "passed": len(targets) >= 2 and not missing,
    }


def prioritize_comparison_evidence(
    documents: list[dict[str, Any]], targets: list[str], limit: int
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for target in targets:
        match = next((doc for doc in documents if document_entity(doc, [target])), None)
        if match is not None and match not in selected:
            selected.append(match)
    selected.extend(doc for doc in documents if doc not in selected)
    return selected[:limit]
