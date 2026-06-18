from langchain_openai import ChatOpenAI

from agent.state import AgentState
from core.config import settings


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

可以优先关注以下方向：

1. RAG 复杂推理优化
   - 可从多跳问答、迭代检索、证据评估等角度改进。

2. GraphRAG / 结构化检索
   - 可引入图结构、实体关系、知识图谱增强检索。

3. 垂直领域 RAG 应用
   - 可选择医疗、法律、教育、科研论文助手等具体场景。

### 错误信息

{error_message}
"""


def build_prompt(state: AgentState) -> str:
    query = state.get("query", "")
    task_type = state.get("task_type", "qa")
    docs_text = build_documents_text(state)

    base_prompt = f"""
你是一个专业的科研论文分析助手。

用户问题：
{query}

任务类型：
{task_type}

检索到的论文内容：
{docs_text}

通用要求：
1. 必须基于检索到的论文内容回答
2. 不要编造论文中没有的信息
3. 如果信息不足，要明确说明
4. 回答要结构化
5. 尽量列出论文标题和链接
6. 不要使用“必发”“一定容易出成果”等绝对化表达
7. 回答控制在 1200 字以内
"""

    if task_type == "compare":
        task_instruction = """
当前任务是论文或方法对比。

请按照以下结构回答：
1. 对比对象概述
2. 表格对比：论文/方法 | 研究问题 | 核心方法 | 可借鉴点
3. 总结适合作为项目改进的方向
"""

    elif task_type == "summarize":
        task_instruction = """
当前任务是论文总结。

请对每篇论文按照以下结构总结：
1. 研究问题
2. 核心方法
3. 主要贡献
4. 可改进点
"""

    elif task_type == "recommend":
        task_instruction = """
当前任务是研究方向推荐。

请按照以下结构回答：
1. 检索论文覆盖的主要方向
2. 推荐 3 个适合切入的研究方向
3. 每个方向说明：
   - 可借鉴论文
   - 为什么适合选题
   - 可以怎么改进
   - 实现难度
4. 给出优先级排序
"""

    else:
        task_instruction = """
当前任务是普通论文问答。

请直接回答用户问题，并引用相关论文作为依据。
"""

    return base_prompt + "\n" + task_instruction


def generate_node(state: AgentState) -> AgentState:
    if not state.get("documents"):
        return {
            "answer": "没有检索到相关论文内容，请尝试换一个更具体的问题。"
        }

    prompt = build_prompt(state)

    try:
        llm = get_llm()
        response = llm.invoke(prompt)

        return {
            "answer": response.content
        }

    except Exception as e:
        error_message = f"{type(e).__name__}: {e}"

        return {
            "answer": build_fallback_answer(state, error_message),
            "error_message": error_message,
            "paper_metadata": {
                **state.get("paper_metadata", {}),
                "generate_error": error_message,
            },
        }