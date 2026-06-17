from agent.state import AgentState
from tools.arxiv_tool import search_arxiv_papers


def build_search_query(user_query: str) -> str:
    """
    将中文问题转换成更适合 arXiv 检索的英文关键词。
    第一版先用简单规则，后面可以升级成 LLM Query Rewriter。
    """
    query = user_query.lower()

    if "rag" in query or "检索增强" in query:
        return "retrieval augmented generation RAG large language models"

    if "graphrag" in query or "graph rag" in query:
        return "GraphRAG graph retrieval augmented generation"

    if "agent" in query or "智能体" in query:
        return "LLM agent tool learning planning memory evaluation"

    if "bert" in query:
        return "BERT language understanding Transformer"

    if "transformer" in query:
        return "Transformer attention mechanism language model"

    return user_query


def retrieve_node(state: AgentState) -> AgentState:
    query = state.get("query", "")
    retry_count = state.get("retry_count", 0)

    search_query = build_search_query(query)

    # 如果是重试，增加检索数量
    max_results = 5 if retry_count == 0 else 8

    papers = search_arxiv_papers(
        query=search_query,
        max_results=max_results,
    )

    documents = []

    for paper in papers:
        documents.append(
            {
                "title": paper["title"],
                "authors": paper["authors"],
                "year": paper["year"],
                "content": paper["summary"],
                "pdf_url": paper["pdf_url"],
                "entry_id": paper["entry_id"],
                "source": paper["source"],
            }
        )

    return {
        "documents": documents,
        "tools_used": state.get("tools_used", []) + ["arxiv_tool"],
        "paper_metadata": {
            "retrieval_source": "arxiv",
            "search_query": search_query,
            "paper_count": len(documents),
        },
    }