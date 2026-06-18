from agent.state import AgentState
from tools.arxiv_tool import search_arxiv_papers


FALLBACK_PAPERS = [
    {
        "title": "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks",
        "authors": ["Patrick Lewis", "Ethan Perez", "Aleksandra Piktus"],
        "year": 2020,
        "content": (
            "RAG combines parametric generation models with non-parametric retrieval. "
            "It retrieves relevant documents and uses them to generate grounded answers."
        ),
        "pdf_url": "https://arxiv.org/abs/2005.11401",
        "entry_id": "2005.11401",
        "source": "fallback",
    },
    {
        "title": "GraphRAG: Graph-based Retrieval-Augmented Generation",
        "authors": ["Research Community"],
        "year": 2024,
        "content": (
            "GraphRAG enhances retrieval-augmented generation by using graph structures "
            "to model relationships between entities, documents, and concepts."
        ),
        "pdf_url": "",
        "entry_id": "",
        "source": "fallback",
    },
]


def retrieve_node(state: AgentState) -> AgentState:
    query = state.get("rewritten_query") or state.get("query", "")
    retry_count = state.get("retry_count", 0)

    max_results = 5 if retry_count == 0 else 8

    papers = search_arxiv_papers(
        query=query,
        max_results=max_results,
    )

    retrieval_source = "arxiv"

    if not papers:
        print("\n[Retrieve Node] arXiv 无返回结果，使用 fallback papers。")
        papers = FALLBACK_PAPERS
        retrieval_source = "fallback"

    documents = []

    for paper in papers:
        documents.append(
            {
                "title": paper.get("title"),
                "authors": paper.get("authors", []),
                "year": paper.get("year"),
                "content": paper.get("summary") or paper.get("content", ""),
                "pdf_url": paper.get("pdf_url"),
                "entry_id": paper.get("entry_id"),
                "source": paper.get("source", retrieval_source),
            }
        )

    return {
        "documents": documents,
        "tools_used": state.get("tools_used", []) + [f"{retrieval_source}_retriever"],
        "paper_metadata": {
            **state.get("paper_metadata", {}),
            "retrieval_source": retrieval_source,
            "search_query": query,
            "paper_count": len(documents),
        },
    }