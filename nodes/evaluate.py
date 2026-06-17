import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from agent.state import AgentState
from prompts.evaluator import EVALUATOR_TEMPLATE

load_dotenv()


def get_llm():
    return ChatOpenAI(
        model=os.getenv("MODEL_NAME", "qwen-plus"),
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL"),
        temperature=0,
    )


def evaluate_node(state: AgentState) -> AgentState:
    query = state.get("query", "")
    documents = state.get("documents", [])

    if not documents:
        return {
            "retrieval_score": 0.0
        }

    docs_text = "\n\n".join(
        [
            f"标题：{doc.get('title')}\n内容：{doc.get('content')}"
            for doc in documents
        ]
    )

    prompt = EVALUATOR_TEMPLATE.format(
        query=query,
        documents=docs_text,
    )

    llm = get_llm()
    response = llm.invoke(prompt)

    try:
        score = float(response.content.strip())
    except ValueError:
        score = 0.5

    score = max(0.0, min(score, 1.0))

    return {
        "retrieval_score": score
    }