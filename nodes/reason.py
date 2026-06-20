from agent.state import AgentState


def reason_node(state: AgentState) -> AgentState:
    """
    判断用户任务类型。
    qa: 普通论文问答
    summarize: 论文总结
    compare: 论文或方法对比
    recommend: 研究方向推荐
    """
    query = state.get("query", "").lower()

    if any(keyword in query for keyword in ["bibtex", "引用", "参考文献", "citation", "cite", "apa", "ieee"]):
        task_type = "citation"

    elif any(word in query for word in ["比较", "对比", "区别", "差异", "compare"]):
        task_type = "compare"

    elif any(word in query for word in ["总结", "概括", "summary", "summarize"]):
        task_type = "summarize"

    elif any(
        word in query
        for word in ["推荐", "方向", "趋势", "热点", "容易出成果", "选题", "借鉴"]
    ):
        task_type = "recommend"

    else:
        task_type = "qa"

    return {
        "task_type": task_type,
        "paper_metadata": {
            **state.get("paper_metadata", {}),
            "task_type": task_type,
        },
    }