from typing import Tuple

from langchain_openai import ChatOpenAI

from agent.state import AgentState
from core.config import settings
from prompts.reason import REASON_TEMPLATE

#原来的关键词判断升级为三层：
#1. rule_based_reason：规则判断 task_type 和 confidence
# 2. llm_reason：规则不确定时调用 LLM 判断
# 3. reason_node：整合最终结果

VALID_TASK_TYPES = {
    "qa",
    "summarize",
    "compare",
    "recommend",
    "citation",
    "pdf_reading",
}

def get_llm():
    return ChatOpenAI(
        model=settings.MODEL_NAME,
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
        temperature=0,
        timeout=settings.LLM_TIMEOUT,
        max_retries=1,
    )


def contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def rule_based_reason(query: str) -> Tuple[str, float]:
    """
    基于关键词进行快速任务分类。

    返回：
    - task_type
    - confidence

    confidence 用来判断规则是否足够确定。
    """

    query_lower = query.lower()

    citation_keywords = [
        "bibtex",
        "apa",
        "ieee",
        "引用",
        "参考文献",
        "citation",
        "cite",
        "reference",
    ]

    summarize_keywords = [
        "总结",
        "概括",
        "归纳",
        "summary",
        "summarize",
        "提炼",
        "梳理",
    ]

    compare_keywords = [
        "对比",
        "比较",
        "区别",
        "差异",
        "compare",
        "comparison",
        "versus",
        "vs",
    ]

    recommend_keywords = [
        "推荐",
        "方向",
        "选题",
        "创新",
        "改进",
        "优化",
        "深入",
        "怎么做",
        "可行",
        "research direction",
        "idea",
        "improve",
    ]

    if contains_any(query_lower, citation_keywords):
        return "citation", 1.0

    if contains_any(query_lower, summarize_keywords):
        return "summarize", 1.0

    if contains_any(query_lower, compare_keywords):
        return "compare", 1.0

    if contains_any(query_lower, recommend_keywords):
        return "recommend", 0.9

    return "qa", 0.5


def llm_reason(query: str) -> str:
    """
    当规则判断置信度较低时，调用 LLM 进行任务分类。只负责分类，不生成答案
    """

    prompt = REASON_TEMPLATE.format(query=query)

    llm = get_llm()
    response = llm.invoke(prompt)

    task_type = response.content.strip().lower()

    if task_type not in VALID_TASK_TYPES:
        return "qa"

    return task_type


def reason_node(state: AgentState) -> AgentState:
    query = state.get("query", "")

    pdf_path = state.get("pdf_path", "")

    if pdf_path:
        return {
            "task_type": "pdf_reading",
            "paper_metadata": {
                **state.get("paper_metadata", {}),
                "reason_source": "pdf_path",
                "reason_confidence": 1.0,
                "rule_task_type": "pdf_reading",
            },
        }

    rule_task_type, confidence = rule_based_reason(query)

    task_type = rule_task_type
    reason_source = "rule"

    if (
        settings.REASON_WITH_LLM
        and confidence < settings.REASON_CONFIDENCE_THRESHOLD
    ):
        try:
            task_type = llm_reason(query)
            reason_source = "llm"

        except Exception as e:
            print(f"[Reason Node Error] LLM fallback failed: {type(e).__name__}: {e}")
            task_type = rule_task_type
            reason_source = "rule_fallback"

    return {
        "task_type": task_type,
        "paper_metadata": {
            **state.get("paper_metadata", {}),
            "reason_source": reason_source,
            "reason_confidence": confidence,
            "rule_task_type": rule_task_type,
        },
    }