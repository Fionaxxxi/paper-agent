from langchain_openai import ChatOpenAI

from agent.state import AgentState
from core.config import settings
from skills.router import get_skill


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


def build_documents_text(state: AgentState) -> str:
    documents = state.get("documents", [])[: settings.MAX_GENERATE_DOCS]

    return "\n\n".join(
        [
            f"论文标题：{doc.get('title')}\n"
            f"作者：{', '.join(doc.get('authors', []))}\n"
            f"年份：{doc.get('year')}\n"
            f"摘要：{truncate_text(doc.get('content', ''))}\n"
            f"链接：{doc.get('pdf_url')}"
            for doc in documents
        ]
    )


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


def generate_node(state: AgentState) -> AgentState:
    if not state.get("documents"):
        return {
            "answer": "没有检索到相关论文内容，请尝试换一个更具体的问题。"
        }

    documents_text = build_documents_text(state)

    skill_state = {
        **state,
        "documents_text": documents_text,
    }

    skill = get_skill(skill_state)
    prompt = skill.build_prompt(skill_state)

    try:
        llm = get_llm()
        response = llm.invoke(prompt)

        return {
            "answer": response.content,
            "paper_metadata": {
                **state.get("paper_metadata", {}),
                "skill_used": skill.name,
            },
        }

    except Exception as e:
        error_message = f"{type(e).__name__}: {e}"

        return {
            "answer": build_fallback_answer(state, error_message),
            "error_message": error_message,
            "paper_metadata": {
                **state.get("paper_metadata", {}),
                "generate_error": error_message,
                "skill_used": skill.name,
            },
        }