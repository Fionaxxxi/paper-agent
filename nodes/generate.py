from langchain_openai import ChatOpenAI

from agent.state import AgentState
from core.config import settings
from core.llm_usage import (
    TrackedLLMError,
    build_llm_usage_update,
    invoke_llm_with_usage,
)
from skills.router import get_skill
from context.context_builder import attach_skill_context


def get_llm():
    return ChatOpenAI(
        model=settings.MODEL_NAME,
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
        temperature=0,
        timeout=settings.LLM_TIMEOUT,
        max_retries=1,
    )


def truncate_text(text: str, max_length: int = settings.DOC_CONTENT_LIMIT) -> str:
    if not text:
        return ""

    if len(text) <= max_length:
        return text

    return text[:max_length] + "...[内容已截断]"



def build_fallback_answer(state: AgentState, error_message: str = "") -> str:
    query = state.get("query", "")
    task_type = state.get("task_type", "qa")
    documents = state.get("documents", [])[: settings.MAX_GENERATE_DOCS]

    paper_lines = []

    for index, doc in enumerate(documents, start=1):
        paper_lines.append(
            f"{index}. {doc.get('title')} ({doc.get('year')})\n"
            f"   链接：{doc.get('pdf_url')}\n"
            f"   简要内容：{truncate_text(doc.get('content', ''), 300)}"
        )

    papers_text = "\n\n".join(paper_lines)

    return f"""## PaperAgent 降级回答

本次大模型生成阶段请求失败，因此先返回基于检索结果的简要分析。

### 用户问题

{query}

### 任务类型

{task_type}

### 检索到的相关论文

{papers_text}

### 初步建议

可以先根据检索到的论文，提取研究问题、核心方法和可改进点，再选择一个范围较小、可实现性较强的方向继续深入。

### 错误信息

{error_message}
"""


def build_low_quality_answer(state: AgentState) -> str:
    """Return an evidence-safe answer without spending another LLM call."""
    documents = state.get("documents", [])[: settings.MAX_GENERATE_DOCS]
    candidate_lines = [
        f"- {doc.get('title', '未命名论文')}"
        for doc in documents
    ]
    candidates = "\n".join(candidate_lines) or "- 暂无可用候选论文"
    replan = state.get("retrieval_replan", {})
    reason = replan.get("reason") or "第二轮检索质量仍低于系统门槛"

    return f"""## 证据不足，已停止继续检索

本次检索已经完成一次受控重规划，但第二轮结果仍不足以支持可靠结论。系统已达到重试预算上限，因此不会继续循环，也不会调用大模型基于低质量证据生成答案。

### 停止原因

{reason}

### 待人工核验的候选论文

{candidates}

建议缩小研究主题、补充作者/论文名/年份等限定信息，或稍后在外部论文数据源恢复后重试。
"""


def generate_node(state: AgentState) -> AgentState:
    task_type = state.get("task_type", "qa")

    if state.get("retrieval_outcome") == "stopped_low_quality":
        return {
            "answer": build_low_quality_answer(state),
            "paper_metadata": {
                **state.get("paper_metadata", {}),
                "answer_mode": "insufficient_evidence",
                "generation_skipped": True,
            },
        }

    if task_type != "pdf_reading" and not state.get("documents"):
        return {
            "answer": "没有检索到相关论文内容，请尝试换一个更具体的问题。"
        }

    if task_type == "pdf_reading" and not state.get("pdf_text"):
        return {
            "answer": f"PDF 文本读取失败，无法进行论文全文分析。错误信息：{state.get('pdf_error', '')}",
            "paper_metadata": {
                **state.get("paper_metadata", {}),
                "skill_used": "pdf_reading",
                "pdf_error": state.get("pdf_error", ""),
            },
        }


    skill_state = attach_skill_context(state)
    skill = get_skill(skill_state)

    if not skill.need_llm:
        return skill.run(skill_state)

    prompt = skill.build_prompt(skill_state)

    try:
        llm = get_llm()
        response, usage_record = invoke_llm_with_usage(
            llm=llm,
            prompt=prompt,
            node_name="generate",
            model_name=settings.MODEL_NAME,
        )
        usage_update = build_llm_usage_update(state, usage_record)

        return {
            **usage_update,
            "answer": response.content,
            "paper_metadata": {
                **skill_state.get("paper_metadata", {}),
                "skill_used": skill.name,
            },
        }

    except TrackedLLMError as error:
        usage_update = build_llm_usage_update(
            state,
            error.usage_record,
        )
        e = error.original_error
        error_message = f"{type(e).__name__}: {e}"

        return {
            **usage_update,
            "answer": build_fallback_answer(state, error_message),
            "error_message": error_message,
            "paper_metadata": {
                **skill_state.get("paper_metadata", {}),
                "generate_error": error_message,
                "skill_used": skill.name,
            },
        }

    except Exception as e:
        error_message = f"{type(e).__name__}: {e}"

        return {
            "answer": build_fallback_answer(state, error_message),
            "error_message": error_message,
            "paper_metadata": {
                **skill_state.get("paper_metadata", {}),
                "generate_error": error_message,
                "skill_used": skill.name,
            },
        }
