import json
import re
from typing import Any

from pydantic import BaseModel, ValidationError

from document_loader.pdf_output_contracts import (
    ChartAnalysisOutput,
    FigureUnderstandingOutput,
    FormulaExplanationOutput,
    TableAnalysisOutput,
)


CONTRACTS: dict[str, type[BaseModel]] = {
    "chart_analysis": ChartAnalysisOutput,
    "figure_understanding": FigureUnderstandingOutput,
    "table_analysis": TableAnalysisOutput,
    "formula_explanation": FormulaExplanationOutput,
}
JSON_BLOCK = re.compile(r"```json\s*(\{.*?\})\s*```", re.IGNORECASE | re.DOTALL)
JSON_FENCE_START = re.compile(r"(?im)^\s*```json\s*$")


def parse_pdf_structured_output(
    answer: str,
    skill_name: str,
    *,
    expected_pages: list[int] | None = None,
    expected_evidence_mode: str | None = None,
) -> tuple[str, dict[str, Any]]:
    contract = CONTRACTS.get(skill_name)
    if contract is None:
        return answer, {"enabled": False, "status": "not_applicable", "valid": True}

    matches = list(JSON_BLOCK.finditer(answer or ""))
    if not matches:
        fence_starts = list(JSON_FENCE_START.finditer(answer or ""))
        if fence_starts:
            fence = fence_starts[-1]
            structured_tail = (answer or "")[fence.end():].lstrip()
            # 专项 PDF Skill 会把机器 JSON 放在答案末尾。模型被截断时没有闭合
            # fence，仍需从用户可读内容中剥离，避免半截 JSON 泄漏到页面。
            if structured_tail.startswith(("{", "[")):
                return (answer or "")[:fence.start()].rstrip(), {
                    "enabled": True,
                    "status": "invalid",
                    "valid": False,
                    "schema": contract.__name__,
                    "error": "truncated_json_block",
                }
        return answer, {
            "enabled": True, "status": "invalid", "valid": False,
            "schema": contract.__name__, "error": "missing_json_block",
        }

    block = matches[-1]
    readable_answer = (answer[:block.start()] + answer[block.end():]).strip()
    try:
        payload = json.loads(block.group(1))
        validated = contract.model_validate(payload)
    except (json.JSONDecodeError, ValidationError) as error:
        return readable_answer, {
            "enabled": True, "status": "invalid", "valid": False,
            "schema": contract.__name__, "error": str(error)[:500],
        }
    scope = validated.evidence_scope
    if expected_pages is not None and scope.pages != expected_pages:
        return readable_answer, {
            "enabled": True, "status": "invalid", "valid": False,
            "schema": contract.__name__, "error": "evidence_pages_mismatch",
        }
    if expected_evidence_mode is not None and scope.evidence_mode != expected_evidence_mode:
        return readable_answer, {
            "enabled": True, "status": "invalid", "valid": False,
            "schema": contract.__name__, "error": "evidence_mode_mismatch",
        }
    return readable_answer, {
        "enabled": True, "status": "valid", "valid": True,
        "schema": contract.__name__, "data": validated.model_dump(mode="json"),
    }
