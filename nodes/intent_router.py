import re

from agent.state import AgentState


SMALLTALK_RESPONSES = {
    "greeting": "你好！我是 PaperAgent，可以帮你检索、阅读、总结和比较论文。",
    "thanks": "不客气！如果你还有论文检索或分析问题，可以继续告诉我。",
    "identity": (
        "我是 PaperAgent，一个证据驱动的科研论文智能体。我可以进行多源论文检索、在线 PDF 全文研究、"
        "个人论文库与公开知识联合分析、方法比较与文献综述、论文图表和公式阅读，并把结论绑定到论文链接、"
        "页码和 Evidence ID；复杂任务还支持受控规划、失败恢复、会话记忆以及 Word/PDF 报告导出。"
    ),
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
    "你是",
    "你能做什么",
    "你可以做什么",
    "你的功能是什么",
}

CAPABILITY_PATTERNS = (
    re.compile(r"(?:你|您)(?:到底)?是(?:谁|什么|哪(?:个|种)(?:助手|系统|agent|智能体)?)?"),
    re.compile(r"(?:介绍|说说|讲讲)(?:一下|下)?(?:你|您)?自己"),
    re.compile(r"(?:你|您).{0,8}(?:能|可以|会).{0,6}(?:做什么|干什么|帮我什么)"),
    re.compile(r"(?:介绍|说说|说明).{0,8}(?:功能|能力|能做什么)"),
    re.compile(r"what (?:can|do) you (?:do|support)"),
)


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
    if len(query) <= 60 and any(pattern.search(query) for pattern in CAPABILITY_PATTERNS):
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
        "retrieval_outcome": "not_applicable",
        "retrieval_stop_reason": "local_response",
        "retrieval_evaluation": {},
        "retrieval_strategy": {"mode": "local", "sources": [], "reason": "local_system_request"},
        "retry_count": 0,
        "retry_query": "",
        "retrieval_replan": {},
        "tools_used": [],
        "token_usage": 0,
        "input_token_usage": 0,
        "output_token_usage": 0,
        "llm_call_count": 0,
        "llm_failed_call_count": 0,
        "llm_usage": [],
        "sub_queries": [],
        "query_plan_enabled": False,
        "research_analysis": {},
        "research_plan": {},
        "research_schedule": {},
        "evidence_store": {"enabled": False, "evidence": [], "evidence_count": 0, "status": "not_applicable"},
        "research_coverage": {"enabled": False, "status": "not_applicable"},
        "repository_evidence": [],
        "repository_enrichment": {},
        "paper_metadata": {
            **metadata,
            "agentic_rag_enabled": False,
            "short_circuited": True,
            "retrieval_source": "local",
            "retrieval_mode": "local",
            "retrieval_count": 0,
            "paper_count": 0,
            "evidence_count": 0,
            "skill_used": "local_response",
            "generation_skipped": True,
        },
    }
