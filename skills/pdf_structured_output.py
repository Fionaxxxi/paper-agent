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
        return readable_answer or answer, {
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
