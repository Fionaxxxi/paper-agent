"""根据 Verifier 反馈最多修复一次最终答案。"""

from agent.state import AgentState
from core.config import settings
from core.llm_usage import (
    TrackedLLMError,
    build_llm_usage_update,
    invoke_llm_with_usage,
)
from nodes.generate import get_llm, truncate_text
from prompts.contracts import get_prompt_version, wrap_untrusted_evidence


def build_answer_repair_prompt(state: AgentState) -> str:
    verification = state.get("answer_verification", {})
    evidence = "\n\n".join(
        f"论文：{doc.get('title', '未命名论文')}\n证据：{truncate_text(doc.get('content', ''), 500)}"
        for doc in state.get("documents", [])[: settings.MAX_GENERATE_DOCS]
    )
    if state.get("pdf_text"):
        evidence = truncate_text(state.get("pdf_text", ""), 2000)

    evidence = wrap_untrusted_evidence(evidence, "答案修复证据")
    return f"""你是 PaperAgent 的答案修复器。只允许根据给定证据修复答案，不得增加证据中不存在的事实。

用户问题：
{state.get('query', '')}

原答案：
{state.get('answer', '')}

Verifier 发现的问题：
{verification.get('issues', [])}

允许使用的证据：
{evidence}

请直接输出修复后的完整中文答案。需要明确提及作为依据的论文标题；证据不足的部分必须明确说明，不要输出分析过程。
"""


def answer_reflect_node(state: AgentState) -> AgentState:
    previous_answer = state.get("answer", "")
    verification = state.get("answer_verification", {})
    reflection = {
        "failure_types": verification.get("failure_types", []),
        "issues": verification.get("issues", []),
        "action": "repair_answer_from_existing_evidence",
        "status": "attempted",
    }
    try:
        response, usage_record = invoke_llm_with_usage(
            llm=get_llm(),
            prompt=build_answer_repair_prompt(state),
            node_name="answer_reflect",
            model_name=settings.MODEL_NAME,
            prompt_version=get_prompt_version("answer_reflect"),
        )
        usage_update = build_llm_usage_update(state, usage_record)
        repaired_answer = str(response.content or "").strip() or previous_answer
        reflection["status"] = "completed"
        return {
            **usage_update,
            "answer": repaired_answer,
            "answer_before_reflection": previous_answer,
            "answer_reflection_count": 1,
            "answer_reflection": reflection,
        }
    except TrackedLLMError as error:
        reflection["status"] = "llm_failed"
        return {
            **build_llm_usage_update(state, error.usage_record),
            "answer": previous_answer,
            "answer_before_reflection": previous_answer,
            "answer_reflection_count": 1,
            "answer_reflection": reflection,
        }
    except Exception as error:
        reflection["status"] = "failed"
        reflection["error_type"] = type(error).__name__
        return {
            "answer": previous_answer,
            "answer_before_reflection": previous_answer,
            "answer_reflection_count": 1,
            "answer_reflection": reflection,
        }
