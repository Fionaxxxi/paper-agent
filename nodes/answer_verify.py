"""将最终答案验证结果写入 LangGraph State。"""

from agent.state import AgentState
from core.config import settings
from validators.answer_quality_validator import AnswerVerification
from validators.answer_quality_validator import verify_answer


def answer_verify_node(state: AgentState) -> AgentState:
    verification = verify_answer(state)
    reflection_count = state.get("answer_reflection_count", 0)
    previous_score = state.get("answer_initial_score", verification.score)
    initial_verification = state.get("answer_initial_verification", {})
    restored = False
    answer = state.get("answer", "")

    if reflection_count > 0 and verification.score <= previous_score:
        answer = state.get("answer_before_reflection", answer)
        restored = True
        if initial_verification:
            verification = AnswerVerification.model_validate(initial_verification)

    if restored:
        stop_reason = "reflection_no_improvement"
    elif reflection_count > 0 and not verification.passed:
        stop_reason = "reflection_budget_exhausted"
    else:
        stop_reason = verification.stop_reason

    return {
        "answer": answer,
        "answer_verification": verification.model_dump(mode="python"),
        "answer_initial_score": (
            verification.score if reflection_count == 0 else previous_score
        ),
        "answer_initial_verification": (
            verification.model_dump(mode="python")
            if reflection_count == 0
            else initial_verification
        ),
        "answer_reflection_restored": restored,
        "answer_stop_reason": stop_reason,
    }


def route_after_answer_verify(state: AgentState) -> str:
    verification = state.get("answer_verification", {})
    if (
        settings.ANSWER_REFLECTION_ENABLED
        and verification.get("should_reflect", False)
        and state.get("answer_reflection_count", 0) < 1
    ):
        return "reflect"
    return "finish"
