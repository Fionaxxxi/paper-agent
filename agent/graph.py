from langgraph.graph import StateGraph, START, END

from agent.state import AgentState
from agent.router import route_after_guardrail, route_after_evaluate
from nodes.guardrail import guardrail_node
from nodes.retrieve import retrieve_node
from nodes.evaluate import evaluate_node
from nodes.generate import generate_node
from nodes.metrics import metrics_node


def retry_node(state: AgentState) -> AgentState:
    return {
        "retry_count": state.get("retry_count", 0) + 1,
    }


def build_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("guardrail", guardrail_node)
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("evaluate", evaluate_node)
    workflow.add_node("retry", retry_node)
    workflow.add_node("generate", generate_node)
    workflow.add_node("metrics", metrics_node)

    workflow.add_edge(START, "guardrail")

    workflow.add_conditional_edges(
        "guardrail",
        route_after_guardrail,
        {
            "retrieve": "retrieve",
            "end": END,
        },
    )

    workflow.add_edge("retrieve", "evaluate")

    workflow.add_conditional_edges(
        "evaluate",
        route_after_evaluate,
        {
            "retry": "retry",
            "generate": "generate",
        },
    )

    workflow.add_edge("retry", "retrieve")
    workflow.add_edge("generate", "metrics")
    workflow.add_edge("metrics", END)

    return workflow.compile()