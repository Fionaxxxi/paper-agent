from nodes.clarification import clarification_node


def state(query, papers=None, topics=None, pending=None):
    return {
        "query": query,
        "pending_clarification": pending or {},
        "paper_metadata": {
            "memory_active_papers": papers or [],
            "memory_active_topics": topics or [],
        },
    }


def test_unique_memory_candidate_resolves_reference_without_llm():
    """作用：只有一个活跃论文时自动补全指代，不打断研究流程。"""
    result = clarification_node(state("它有什么局限？", papers=["ReAct"]))
    assert result["clarification_required"] is False
    assert result["query"] == "ReAct有什么局限？"
    assert result["resolved_referent"] == "ReAct"


def test_multiple_candidates_request_clarification_and_short_circuit():
    """作用：两个可能对象时主动询问，不检索或猜测其中一个。"""
    result = clarification_node(
        state("它有什么局限？", papers=["ReAct", "Reflexion"])
    )
    assert result["clarification_required"] is True
    assert result["task_type"] == "clarification"
    assert result["documents"] == []
    assert "ReAct" in result["answer"] and "Reflexion" in result["answer"]
    assert result["paper_metadata"]["short_circuited"] is True


def test_missing_candidate_requests_explicit_object_name():
    """作用：没有上下文候选时要求论文或方法名称。"""
    result = clarification_node(state("这个方法效果怎么样？"))
    assert result["clarification_required"] is True
    assert "论文、方法或模型名称" in result["answer"]


def test_followup_candidate_restores_pending_query():
    """作用：用户回答候选名称后恢复原问题并清除等待状态。"""
    pending = {
        "query": "它有什么局限？",
        "candidates": ["ReAct", "Reflexion"],
        "references": ["它"],
    }
    result = clarification_node(state("Reflexion", pending=pending))
    assert result["query"] == "Reflexion有什么局限？"
    assert result["pending_clarification"] == {}
    assert result["clarification_required"] is False
