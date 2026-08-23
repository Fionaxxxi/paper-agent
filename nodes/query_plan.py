from typing import Any, Dict, List

from agent.state import AgentState
from retrieval.research_query import build_research_search_query


COMPLEX_TASK_TYPES = {"compare", "summarize", "recommend", "citation"}

COMPLEX_QUERY_KEYWORDS = {
    "compare",
    "comparison",
    "difference",
    "differences",
    "versus",
    " vs ",
    "survey",
    "summarize",
    "summary",
    "review",
    "limitations",
    "challenges",
    "future directions",
    "research directions",
    "open problems",
    "recommend",
    "recommendation",
    "citation",
    "bibtex",
    "比较",
    "对比",
    "区别",
    "差异",
    "综述",
    "总结",
    "概括",
    "局限",
    "挑战",
    "未来方向",
    "研究方向",
    "开放问题",
    "推荐",
    "引用",
    "参考文献",
}


def deduplicate_queries(queries: List[str]) -> List[str]:
    """
    Deduplicate query strings while preserving order.
    """

    seen = set()
    deduplicated = []

    for query in queries:
        normalized_query = query.strip()

        if not normalized_query:
            continue

        key = normalized_query.lower()

        if key in seen:
            continue

        seen.add(key)
        deduplicated.append(normalized_query)

    return deduplicated


def classify_query_complexity(state: Dict[str, Any]) -> Dict[str, str]:
    """
    Classify retrieval complexity without calling an LLM.

    Explicit complex task types take priority. When task_type has not been
    classified yet, the original user query provides a conservative signal.
    Short single-purpose questions use one retrieval query by default.
    """

    task_type = state.get("task_type", "qa")
    if task_type == "pdf_reading":
        return {
            "query_complexity": "not_applicable",
            "complexity_reason": "pdf_reading skips external retrieval",
        }

    if task_type in COMPLEX_TASK_TYPES:
        return {
            "query_complexity": "complex",
            "complexity_reason": f"complex task_type: {task_type}",
        }

    query = str(state.get("query", "")).strip().lower()
    matched_keywords = sorted(
        keyword.strip()
        for keyword in COMPLEX_QUERY_KEYWORDS
        if keyword in query
    )
    if matched_keywords:
        return {
            "query_complexity": "complex",
            "complexity_reason": (
                "complex query keyword: " + ", ".join(matched_keywords)
            ),
        }

    return {
        "query_complexity": "simple",
        "complexity_reason": "single-purpose question",
    }


def build_rule_based_sub_queries(state: Dict[str, Any]) -> List[str]:
    """
    Build sub queries using lightweight rules.

    This is the first version of Query Planning. It avoids extra LLM calls
    and keeps the Agentic RAG stage stable.
    """

    query = state.get("query", "")
    rewritten_query = state.get("rewritten_query", "") or query
    task_type = state.get("task_type", "qa")

    sub_queries = [rewritten_query]
    complexity = classify_query_complexity(state)["query_complexity"]

    if complexity == "simple":
        return deduplicate_queries(sub_queries)

    if task_type == "compare":
        sub_queries.extend(
            [
                f"{rewritten_query} methods comparison",
                f"{rewritten_query} evaluation metrics",
                f"{rewritten_query} limitations",
            ]
        )

    elif task_type == "summarize":
        sub_queries.extend(
            [
                f"{rewritten_query} survey overview",
                f"{rewritten_query} methods",
                f"{rewritten_query} contributions",
            ]
        )

    elif task_type == "recommend":
        sub_queries.extend(
            [
                f"{rewritten_query} open problems",
                f"{rewritten_query} future research directions",
                f"{rewritten_query} limitations challenges",
            ]
        )

    elif task_type == "citation":
        sub_queries.extend(
            [
                f"{rewritten_query} arxiv",
                f"{rewritten_query} recent papers",
            ]
        )

    else:
        sub_queries.extend(
            [
                f"{rewritten_query} recent research",
                f"{rewritten_query} methods",
            ]
        )

    return deduplicate_queries(sub_queries)


def query_plan_node(state: AgentState) -> AgentState:
    """
    Build retrieval sub_queries for Agentic RAG.

    PDF reading tasks do not need query planning because they analyze
    uploaded PDF text directly.
    """

    task_type = state.get("task_type", "qa")
    complexity_result = classify_query_complexity(state)

    if task_type == "pdf_reading":
        return {
            "sub_queries": [],
            "query_plan_enabled": False,
            "query_plan_reason": "pdf_reading task does not require retrieval planning",
            **complexity_result,
        }

    research_plan = state.get("research_plan", {})
    if (
        state.get("task_level") in {"L2", "L3"}
        and state.get("research_plan_validation", {}).get("valid")
        and research_plan.get("tasks")
    ):
        sub_queries = deduplicate_queries([
            build_research_search_query(state, task.get("objective", ""))
            for task in research_plan["tasks"]
            if task.get("source") != "evidence_store"
        ])
        return {
            "sub_queries": sub_queries,
            "query_plan_enabled": True,
            "query_plan_reason": "planner_lite" if state.get("task_level") == "L2" else "structured_research_plan",
            "query_complexity": "complex",
            "complexity_reason": "L3 validated research plan",
            "paper_metadata": {
                **state.get("paper_metadata", {}),
                "sub_queries": sub_queries,
                "sub_query_count": len(sub_queries),
                "planned_query_count": len(sub_queries),
                "query_plan_enabled": True,
                "query_plan_reason": "planner_lite" if state.get("task_level") == "L2" else "structured_research_plan",
                "query_complexity": "complex",
                "complexity_reason": "L3 validated research plan",
            },
        }

    sub_queries = build_rule_based_sub_queries(state)
    query_complexity = complexity_result["query_complexity"]
    query_plan_reason = (
        "single_query_for_simple_question"
        if query_complexity == "simple"
        else "multi_query_for_complex_question"
    )

    return {
        "sub_queries": sub_queries,
        "query_plan_enabled": True,
        "query_plan_reason": query_plan_reason,
        **complexity_result,
        "paper_metadata": {
            **state.get("paper_metadata", {}),
            "sub_queries": sub_queries,
            "sub_query_count": len(sub_queries),
            "planned_query_count": len(sub_queries),
            "query_plan_enabled": True,
            "query_plan_reason": query_plan_reason,
            **complexity_result,
        },
    }
