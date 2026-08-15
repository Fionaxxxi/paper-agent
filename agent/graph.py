from langgraph.graph import StateGraph, START, END

from agent.state import AgentState
from agent.router import route_after_evaluate

from nodes.query_rewrite import query_rewrite_node
from nodes.retrieve import retrieve_node
from nodes.evaluate import evaluate_node
from nodes.reason import reason_node
from nodes.generate import generate_node
from nodes.metrics import metrics_node
from nodes.query_plan import query_plan_node
from nodes.intent_router import intent_router_node
from nodes.retrieval_replan import build_retrieval_replan
from nodes.answer_verify import answer_verify_node, route_after_answer_verify
from nodes.answer_reflect import answer_reflect_node
from nodes.research_analyze import research_analyze_node
from nodes.clarification import clarification_node
from nodes.research_schedule import research_schedule_node
from nodes.evidence_store import evidence_store_node
from nodes.repository_enrich import repository_enrich_node
from nodes.research_coverage import research_coverage_node
from nodes.research_citation_validate import research_citation_validate_node
from nodes.research_citation_repair import research_citation_repair_node
from nodes.pdf_grounding_validate import pdf_grounding_validate_node

from utils.timer import timed_node


def retry_node(state: AgentState) -> AgentState:
    return build_retrieval_replan(state)


def route_after_intent(state: AgentState) -> str:
    if state.get("input_intent") == "research":
        return "clarification"

    return "end"


def route_after_clarification(state: AgentState) -> str:
    return "end" if state.get("clarification_required") else "analyze"

def route_after_query_rewrite(state):
    """
    如果请求中包含 pdf_path，说明是 PDF 阅读任务，
    直接进入 Reason Node，不再执行 Query Plan / Retrieve / Evaluate / Retry。
    """
    if state.get("pdf_path"):
        return "reason"

    return "query_plan"

def build_graph(checkpointer=None):
    workflow = StateGraph(AgentState)

    workflow.add_node(
        "intent_router",
        timed_node("intent_router", intent_router_node),
    )
    workflow.add_node(
        "clarification",
        timed_node("clarification", clarification_node),
    )

    workflow.add_node(
        "query_rewrite",
        timed_node("query_rewrite", query_rewrite_node),
    )
    workflow.add_node(
        "research_analyze",
        timed_node("research_analyze", research_analyze_node),
    )

    workflow.add_node(
        "query_plan",
        timed_node("query_plan", query_plan_node),
    )

    workflow.add_node(
        "retrieve",
        timed_node("retrieve", retrieve_node),
    )

    workflow.add_node(
        "evaluate",
        timed_node("evaluate", evaluate_node),
    )

    workflow.add_node(
        "retry",
        timed_node("retry", retry_node),
    )

    workflow.add_node(
        "reason",
        timed_node("reason", reason_node),
    )

    workflow.add_node(
        "generate",
        timed_node("generate", generate_node),
    )
    workflow.add_node(
        "research_citation_validate",
        timed_node("research_citation_validate", research_citation_validate_node),
    )
    workflow.add_node(
        "research_citation_repair",
        timed_node("research_citation_repair", research_citation_repair_node),
    )
    workflow.add_node(
        "pdf_grounding_validate",
        timed_node("pdf_grounding_validate", pdf_grounding_validate_node),
    )

    workflow.add_node(
        "metrics",
        timed_node("metrics", metrics_node),
    )

    workflow.add_edge(START, "intent_router")
    workflow.add_conditional_edges(
        "intent_router",
        route_after_intent,
        {
            "clarification": "clarification",
            "end": END,
        },
    )
    workflow.add_node(
        "research_schedule",
        timed_node("research_schedule", research_schedule_node),
    )
    workflow.add_node(
        "evidence_store",
        timed_node("evidence_store", evidence_store_node),
    )
    workflow.add_node(
        "repository_enrich",
        timed_node("repository_enrich", repository_enrich_node),
    )
    workflow.add_node(
        "research_coverage",
        timed_node("research_coverage", research_coverage_node),
    )
    workflow.add_conditional_edges(
        "clarification",
        route_after_clarification,
        {"analyze": "research_analyze", "end": END},
    )
    workflow.add_edge("research_analyze", "query_rewrite")
    workflow.add_node(
        "answer_verify",
        timed_node("answer_verify", answer_verify_node),
    )
    workflow.add_node(
        "answer_reflect",
        timed_node("answer_reflect", answer_reflect_node),
    )
    workflow.add_conditional_edges(
        "query_rewrite",
        route_after_query_rewrite,
        {
            "reason": "reason",
            "query_plan": "query_plan",
        },
    )

    workflow.add_edge("query_plan", "research_schedule")
    workflow.add_edge("research_schedule", "retrieve")
    workflow.add_edge("retrieve", "repository_enrich")
    workflow.add_edge("repository_enrich", "evidence_store")
    workflow.add_edge("evidence_store", "research_coverage")
    workflow.add_edge("research_coverage", "evaluate")

    workflow.add_conditional_edges(
        "evaluate",
        route_after_evaluate,
        {
            "retry": "retry",
            "generate": "reason",
        },
    )

    workflow.add_edge("retry", "retrieve")
    workflow.add_edge("reason", "generate")
    workflow.add_edge("generate", "research_citation_validate")
    workflow.add_edge("research_citation_validate", "research_citation_repair")
    workflow.add_edge("research_citation_repair", "pdf_grounding_validate")
    workflow.add_edge("pdf_grounding_validate", "answer_verify")
    workflow.add_conditional_edges(
        "answer_verify",
        route_after_answer_verify,
        {
            "reflect": "answer_reflect",
            "finish": "metrics",
        },
    )
    workflow.add_edge("answer_reflect", "pdf_grounding_validate")
    workflow.add_edge("metrics", END)

    return workflow.compile(checkpointer=checkpointer)
