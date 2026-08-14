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

from utils.timer import timed_node


def retry_node(state: AgentState) -> AgentState:
    return build_retrieval_replan(state)


def route_after_intent(state: AgentState) -> str:
    if state.get("input_intent") == "research":
        return "query_rewrite"

    return "end"

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
        "metrics",
        timed_node("metrics", metrics_node),
    )

    workflow.add_edge(START, "intent_router")
    workflow.add_conditional_edges(
        "intent_router",
        route_after_intent,
        {
            "query_rewrite": "research_analyze",
            "end": END,
        },
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

    workflow.add_edge("query_plan", "retrieve")
    workflow.add_edge("retrieve", "evaluate")

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
    workflow.add_edge("generate", "answer_verify")
    workflow.add_conditional_edges(
        "answer_verify",
        route_after_answer_verify,
        {
            "reflect": "answer_reflect",
            "finish": "metrics",
        },
    )
    workflow.add_edge("answer_reflect", "answer_verify")
    workflow.add_edge("metrics", END)

    return workflow.compile(checkpointer=checkpointer)
