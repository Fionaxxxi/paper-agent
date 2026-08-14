"""最终答案的确定性质量检查与有限 Reflection 决策。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AnswerVerification(BaseModel):
    passed: bool
    score: float = Field(ge=0.0, le=1.0)
    failure_types: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)
    should_reflect: bool = False
    stop_reason: str = ""


def _has_task_structure(answer: str, task_type: str) -> bool:
    keywords_by_task = {
        "compare": ("对比", "比较", "差异", "共同"),
        "summarize": ("方法", "贡献", "局限", "总结"),
        "recommend": ("方向", "建议", "风险", "可行"),
    }
    keywords = keywords_by_task.get(task_type)
    if not keywords:
        return True
    return sum(keyword in answer for keyword in keywords) >= 2


def _has_evidence_signal(answer: str, documents: list[dict[str, Any]]) -> bool:
    if not documents:
        return True
    if "资料不足" in answer or "证据不足" in answer:
        return True
    normalized_answer = answer.casefold()
    return any(
        title.casefold() in normalized_answer
        for document in documents
        if (title := str(document.get("title") or "").strip())
    )


def verify_answer(state: dict[str, Any]) -> AnswerVerification:
    answer = str(state.get("answer") or "").strip()
    metadata = state.get("paper_metadata", {})
    answer_mode = metadata.get("answer_mode", "normal")

    if answer_mode == "insufficient_evidence":
        return AnswerVerification(
            passed=True,
            score=1.0,
            stop_reason="insufficient_evidence_already_disclosed",
        )

    checks: list[tuple[bool, float, str, str]] = [
        (bool(answer), 0.4, "empty_answer", "最终答案为空。"),
        (
            len(answer) >= 40,
            0.2,
            "answer_too_short",
            "答案过短，可能没有完整回答研究问题。",
        ),
        (
            _has_task_structure(answer, state.get("task_type", "qa")),
            0.2,
            "missing_task_structure",
            "答案缺少当前任务所需的比较、总结或建议结构。",
        ),
        (
            _has_evidence_signal(answer, state.get("documents", [])),
            0.2,
            "missing_evidence_reference",
            "答案没有提及任何已检索论文标题，也没有披露资料不足。",
        ),
    ]
    score = round(sum(weight for passed, weight, _, _ in checks if passed), 2)
    failures = [failure for passed, _, failure, _ in checks if not passed]
    issues = [issue for passed, _, _, issue in checks if not passed]
    has_repair_context = bool(state.get("documents") or state.get("pdf_text"))
    should_reflect = bool(failures and has_repair_context and not state.get("error_message"))

    return AnswerVerification(
        passed=not failures,
        score=score,
        failure_types=failures,
        issues=issues,
        should_reflect=should_reflect,
        stop_reason=(
            "passed"
            if not failures
            else ("repairable_answer_defect" if should_reflect else "no_repair_context")
        ),
    )
