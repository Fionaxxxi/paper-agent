from agent.state import AgentState


def guardrail_node(state: AgentState) -> AgentState:
    query = state.get("query", "").strip()

    if len(query) < 3:
        return {
            "is_valid": False,
            "answer": "问题过短，请输入更具体的论文分析问题。",
            "error_message": "query_too_short",
        }

    forbidden_keywords = ["破解", "盗取", "攻击", "违法"]

    if any(word in query for word in forbidden_keywords):
        return {
            "is_valid": False,
            "answer": "该问题可能涉及不安全内容，无法处理。",
            "error_message": "unsafe_query",
        }

    return {
        "is_valid": True,
        "error_message": None,
    }