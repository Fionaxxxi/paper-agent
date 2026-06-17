import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from agent.state import AgentState
from prompts.qa import QA_TEMPLATE

load_dotenv()


def get_llm():
    return ChatOpenAI(
        model=os.getenv("MODEL_NAME", "qwen-plus"),
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL"),
        temperature=0,
    )


def generate_node(state: AgentState) -> AgentState:
    query = state.get("query", "")
    documents = state.get("documents", [])

    if not documents:
        return {
            "answer": "没有检索到相关论文内容，请尝试换一个更具体的问题。"
        }

    docs_text = "\n\n".join(
        [
            f"标题：{doc.get('title')}\n"
            f"作者：{', '.join(doc.get('authors', []))}\n"
            f"年份：{doc.get('year')}\n"
            f"内容：{doc.get('content')}"
            for doc in documents
        ]
    )

    prompt = QA_TEMPLATE.format(
        query=query,
        documents=docs_text,
    )

    llm = get_llm()
    response = llm.invoke(prompt)

    return {
        "answer": response.content
    }