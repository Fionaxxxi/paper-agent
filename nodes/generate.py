import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from agent.state import AgentState

load_dotenv()


def get_llm():
    return ChatOpenAI(
        model=os.getenv("MODEL_NAME", "qwen-plus"),
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL"),
        temperature=0,
        timeout=60,
    )


def build_documents_text(state: AgentState) -> str:
    documents = state.get("documents", [])

    return "\n\n".join(
        [
            f"论文标题：{doc.get('title')}\n"
            f"作者：{', '.join(doc.get('authors', []))}\n"
            f"年份：{doc.get('year')}\n"
            f"摘要：{doc.get('content')}\n"
            f"链接：{doc.get('pdf_url')}"
            for doc in documents
        ]
    )


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
"""

    if task_type == "compare":
        task_instruction = """
当前任务是论文或方法对比。

请按照以下结构回答：
1. 对比对象概述
2. 表格对比：
   论文/方法 | 研究问题 | 核心方法 | 优势 | 局限 | 可借鉴点
3. 总结哪类方法更适合作为项目或论文改进方向
"""

    elif task_type == "summarize":
        task_instruction = """
当前任务是论文总结。

请对每篇论文按照以下结构总结：
1. 研究问题
2. 核心方法
3. 实验结果
4. 主要贡献
5. 局限性
6. 可复现或可改进点
"""

    elif task_type == "recommend":
        task_instruction = """
当前任务是研究方向推荐。

请按照以下结构回答：
1. 先总结检索到的论文覆盖了哪些方向
2. 给出 3-5 个相对适合切入的研究方向
3. 每个方向说明：
   - 可以借鉴的论文
   - 为什么适合作为选题
   - 可以怎么改进
   - 实现难度
4. 最后给出优先级排序
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

    llm = get_llm()
    response = llm.invoke(prompt)

    return {
        "answer": response.content
    }