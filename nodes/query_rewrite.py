from agent.state import AgentState


def query_rewrite_node(state: AgentState) -> AgentState:
    """
    将用户问题改写成更适合 arXiv 检索的英文关键词。
    第一版先使用规则改写，后续可以升级为 LLM Query Rewrite。
    """
    original_query = state.get("query", "")
    query = original_query.lower()

    if "rag" in query or "检索增强" in query:
        rewritten_query = (
            "retrieval augmented generation RAG large language models "
            "recent research directions"
        )

    elif "graphrag" in query or "graph rag" in query:
        rewritten_query = (
            "GraphRAG graph retrieval augmented generation "
            "large language models"
        )

    elif "agent" in query or "智能体" in query:
        rewritten_query = (
            "LLM agent tool learning planning memory evaluation "
            "large language models"
        )

    elif "多模态" in query or "multimodal" in query:
        rewritten_query = (
            "multimodal retrieval augmented generation "
            "large language models"
        )

    elif "文献综述" in query or "论文综述" in query:
        rewritten_query = (
            "automatic literature review retrieval augmented generation "
            "large language models"
        )

    elif "transformer" in query:
        rewritten_query = "Transformer self attention language model"

    elif "bert" in query:
        rewritten_query = "BERT bidirectional transformer language understanding"

    else:
        rewritten_query = original_query

    return {
        "rewritten_query": rewritten_query,
        "paper_metadata": {
            **state.get("paper_metadata", {}),
            "original_query": original_query,
            "rewritten_query": rewritten_query,
        },
    }