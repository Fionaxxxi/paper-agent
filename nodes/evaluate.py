import re

from langchain_openai import ChatOpenAI

from agent.state import AgentState
from core.config import settings
from prompts.evaluator import EVALUATOR_TEMPLATE


def get_llm():
    return ChatOpenAI(
        model=settings.MODEL_NAME,
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
        temperature=0,
        timeout=settings.LLM_TIMEOUT,
        max_retries=1,
    )


def rule_based_score(state: AgentState) -> float:
    query = state.get("query", "").lower()
    rewritten_query = state.get("rewritten_query", "").lower()
    documents = state.get("documents", [])

    if not documents:
        return 0.0

    query_text = query + " " + rewritten_query

    keywords = [
        word.strip()
        for word in re.split(r"\s+|,|，|。|？|\?", query_text)
        if len(word.strip()) > 2
    ]

    hit_count = 0

    for doc in documents:
        text = f"{doc.get('title', '')} {doc.get('content', '')}".lower()

        if any(keyword in text for keyword in keywords):
            hit_count += 1

    if hit_count == 0:
        return 0.5

    score = 0.5 + hit_count / len(documents) * 0.5
    return round(min(score, 1.0), 2)


def llm_score(state: AgentState) -> float:
    query = state.get("query", "")
    documents = state.get("documents", [])[:3]

    docs_text = "\n\n".join(
        [
            f"标题：{doc.get('title')}\n摘要：{doc.get('content', '')[:500]}"
            for doc in documents
        ]
    )

    prompt = EVALUATOR_TEMPLATE.format(
        query=query,
        documents=docs_text,
    )

    llm = get_llm()
    response = llm.invoke(prompt)

    text = response.content.strip()
    match = re.search(r"0(\.\d+)?|1(\.0+)?", text)

    if match:
        return float(match.group())

    return 0.5


def evaluate_node(state: AgentState) -> AgentState:
    try:
        if settings.EVALUATE_WITH_LLM:
            score = llm_score(state)
        else:
            score = rule_based_score(state)

    except Exception as e:
        print(f"[Evaluate Node Error] {type(e).__name__}: {e}")
        score = rule_based_score(state)

    return {
        "retrieval_score": max(0.0, min(score, 1.0)),
    }