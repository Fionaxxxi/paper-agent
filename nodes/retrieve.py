from agent.state import AgentState
from core.config import settings
from retrieval.cache import load_cached_papers, save_cached_papers
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


def convert_papers_to_documents(papers, source: str):
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
                "source": paper.get("source", source),
            }
        )

    return documents


def retrieve_node(state: AgentState) -> AgentState:
    query = state.get("rewritten_query") or state.get("query", "")
    retry_count = state.get("retry_count", 0)

    max_results = settings.ARXIV_MAX_RESULTS

    if retry_count > 0:
        max_results = min(max_results + 2, 8)

    retrieval_mode = settings.RETRIEVAL_MODE.lower()

    papers = []
    retrieval_source = retrieval_mode
    cache_hit = False

    if retrieval_mode == "arxiv":
        cached_papers = load_cached_papers(query)

        if cached_papers is not None:
            print("\n[Retrieve Node] Cache hit，使用本地缓存结果。")
            papers = cached_papers
            retrieval_source = "cache"
            cache_hit = True

        else:
            print("\n[Retrieve Node] Cache miss，调用 arXiv 检索。")

            papers = search_arxiv_papers(
                query=query,
                max_results=max_results,
            )

            if papers:
                save_cached_papers(query, papers)
                print("[Retrieve Node] arXiv 检索结果已写入缓存。")
                retrieval_source = "arxiv"
                cache_hit = False

            else:
                print("\n[Retrieve Node] arXiv 无返回结果，使用 fallback papers。")
                papers = FALLBACK_PAPERS
                retrieval_source = "fallback"
                cache_hit = False

    else:
        print("\n[Retrieve Node] 当前使用 fallback 检索模式，不访问 arXiv。")
        papers = FALLBACK_PAPERS
        retrieval_source = "fallback"
        cache_hit = False

    documents = convert_papers_to_documents(papers, retrieval_source)

    return {
        "documents": documents,
        "tools_used": state.get("tools_used", []) + [f"{retrieval_source}_retriever"],
        "paper_metadata": {
            **state.get("paper_metadata", {}),
            "retrieval_source": retrieval_source,
            "search_query": query,
            "paper_count": len(documents),
            "retrieval_mode": retrieval_mode,
            "cache_hit": cache_hit,
        },
    }