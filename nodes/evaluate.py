import re

from langchain_openai import ChatOpenAI

from agent.state import AgentState
from core.config import settings
from core.llm_usage import (
    TrackedLLMError,
    build_llm_usage_update,
    invoke_llm_with_usage,
)
from prompts.evaluator import EVALUATOR_TEMPLATE
from prompts.contracts import get_prompt_version, wrap_untrusted_evidence
from retrieval.comparison import comparison_coverage, comparison_targets
from retrieval.research_query import (
    core_topic_terms, document_matches_topic, required_topic_groups,
    topic_group_coverage,
)


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

    hard_coverage = topic_group_coverage(documents, required_topic_groups(state))
    if hard_coverage["enabled"] and not hard_coverage["passed"]:
        return 0.58 if hard_coverage["covered_groups"] else 0.4

    targets = comparison_targets(query, state.get("task_type", ""))
    coverage = comparison_coverage(documents, targets)
    if coverage["enabled"]:
        if coverage["passed"]:
            return 0.85
        if coverage["covered_entities"]:
            return 0.55
        return 0.4

    query_text = query + " " + rewritten_query

    topic_terms = core_topic_terms(state)
    topic_hit_count = sum(
        document_matches_topic(document, topic_terms) for document in documents
    )
    if state.get("task_level") in {"L2", "L3"} and topic_terms:
        if topic_hit_count >= 3:
            ratio = topic_hit_count / len(documents)
            return round(min(0.75 + 0.15 * ratio, 0.9), 2)
        if topic_hit_count == 2:
            return 0.72
        if topic_hit_count == 1:
            return 0.58

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


def llm_score_with_usage(state: AgentState):
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
        documents=wrap_untrusted_evidence(docs_text, "检索质量评估材料"),
    )

    llm = get_llm()
    response, usage_record = invoke_llm_with_usage(
        llm=llm,
        prompt=prompt,
        node_name="evaluate",
        model_name=settings.MODEL_NAME,
        prompt_version=get_prompt_version("evaluate"),
    )

    text = response.content.strip()
    match = re.search(r"0(\.\d+)?|1(\.0+)?", text)

    if match:
        return float(match.group()), usage_record

    return 0.5, usage_record


def llm_score(state: AgentState) -> float:
    score, _ = llm_score_with_usage(state)
    return score


def evaluate_node(state: AgentState) -> AgentState:
    usage_update = {}

    try:
        if settings.EVALUATE_WITH_LLM:
            score, usage_record = llm_score_with_usage(state)
            usage_update = build_llm_usage_update(state, usage_record)
        else:
            score = rule_based_score(state)

    except TrackedLLMError as error:
        usage_update = build_llm_usage_update(
            state,
            error.usage_record,
        )
        e = error.original_error
        print(f"[Evaluate Node Error] {type(e).__name__}: {e}")
        score = rule_based_score(state)

    except Exception as e:
        print(f"[Evaluate Node Error] {type(e).__name__}: {e}")
        score = rule_based_score(state)

    retry_count = state.get("retry_count", 0)
    requested_scope_unavailable = (
        state.get("retrieval_strategy", {}).get("mode") == "unavailable"
    )
    if requested_scope_unavailable:
        retrieval_outcome = "stopped_low_quality"
        retrieval_stop_reason = "requested_scope_unavailable"
    elif score >= 0.7:
        retrieval_outcome = "recovered" if retry_count > 0 else "accepted"
        retrieval_stop_reason = "quality_threshold_met"
    elif retry_count > 0:
        retrieval_outcome = "stopped_low_quality"
        retrieval_stop_reason = "retry_budget_exhausted"
    else:
        retrieval_outcome = "replan_required"
        retrieval_stop_reason = "quality_below_threshold"

    targets = comparison_targets(state.get("query", ""), state.get("task_type", ""))
    comparison_check = comparison_coverage(state.get("documents", []), targets)
    topic_coverage = topic_group_coverage(
        state.get("documents", []), required_topic_groups(state)
    )
    failure_type = ""
    if comparison_check["enabled"] and not comparison_check["passed"]:
        failure_type = "source_coverage_missing"
    elif topic_coverage["enabled"] and not topic_coverage["passed"]:
        failure_type = "topic_coverage_missing"
    elif score < 0.7:
        failure_type = "quality_below_threshold"

    return {
        **usage_update,
        "retrieval_score": max(0.0, min(score, 1.0)),
        "retrieval_outcome": retrieval_outcome,
        "retrieval_stop_reason": retrieval_stop_reason,
        "retrieval_evaluation": {
            "failure_type": failure_type,
            "comparison_coverage": comparison_check,
            "topic_coverage": topic_coverage,
        },
    }
