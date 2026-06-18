from langgraph.graph import StateGraph, START, END

from agent.state import AgentState
from agent.router import route_after_evaluate

from nodes.query_rewrite import query_rewrite_node
from nodes.retrieve import retrieve_node
from nodes.evaluate import evaluate_node
from nodes.reason import reason_node
from nodes.generate import generate_node
from nodes.metrics import metrics_node

from utils.timer import timed_node


def retry_node(state: AgentState) -> AgentState:
    return {
        "retry_count": state.get("retry_count", 0) + 1,
    }


def build_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node(
        "query_rewrite",
        timed_node("query_rewrite", query_rewrite_node),
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

    workflow.add_edge(START, "query_rewrite")
    workflow.add_edge("query_rewrite", "retrieve")
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
    workflow.add_edge("generate", "metrics")
    workflow.add_edge("metrics", END)

    return workflow.compile()