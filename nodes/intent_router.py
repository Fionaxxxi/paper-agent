import re

from agent.state import AgentState


SMALLTALK_RESPONSES = {
    "greeting": "你好！我是 PaperAgent，可以帮你检索、阅读、总结和比较论文。",
    "thanks": "不客气！如果你还有论文检索或分析问题，可以继续告诉我。",
    "identity": "我是 PaperAgent，专门协助论文检索、阅读、总结、比较和研究方向分析。",
}

GREETING_MESSAGES = {
    "hi",
    "hello",
    "hey",
    "你好",
    "您好",
    "早上好",
    "下午好",
    "晚上好",
}

THANKS_MESSAGES = {
    "thanks",
    "thank you",
    "谢谢",
    "多谢",
    "感谢",
}

IDENTITY_MESSAGES = {
    "who are you",
    "what can you do",
    "你是谁",
    "你能做什么",
    "你可以做什么",
    "你的功能是什么",
}


def normalize_message(query: str) -> str:
    """Normalize a short message without changing its semantic content."""

    normalized = query.strip().casefold()
    normalized = re.sub(r"[\s]+", " ", normalized)
    return normalized.strip(" ,.?!，。？！~～")


def classify_input_intent(state: AgentState) -> str:
    """Classify only high-confidence small-talk; everything else uses RAG."""

    if state.get("pdf_path"):
        return "research"

    query = normalize_message(state.get("query", ""))

    if query in GREETING_MESSAGES:
        return "greeting"
    if query in THANKS_MESSAGES:
        return "thanks"
    if query in IDENTITY_MESSAGES:
        return "identity"

    return "research"


def intent_router_node(state: AgentState) -> AgentState:
    """Return a local answer for small-talk or mark the request for RAG."""

    intent = classify_input_intent(state)
    metadata = {
        **state.get("paper_metadata", {}),
        "input_intent": intent,
    }

    if intent == "research":
        return {
            "input_intent": intent,
            "paper_metadata": metadata,
        }

    return {
        "input_intent": intent,
        "task_type": "smalltalk",
        "answer": SMALLTALK_RESPONSES[intent],
        "documents": [],
        "retrieval_score": 0.0,
        "tools_used": list(state.get("tools_used", [])),
        "token_usage": state.get("token_usage", 0),
        "paper_metadata": {
            **metadata,
            "agentic_rag_enabled": False,
            "short_circuited": True,
        },
    }
