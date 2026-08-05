from typing import Any, Dict, List

from agent.state import AgentState
from core.config import settings
from retrieval.cache import load_cached_papers, save_cached_papers
from retrieval.result_merger import merge_documents_with_stats
from tools.runtime import paper_tool_executor, paper_tool_router


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


def convert_papers_to_documents(papers: List[Dict[str, Any]], source: str) -> List[Dict[str, Any]]:
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


def get_max_results(state: AgentState) -> int:
    """
    Decide max retrieval results according to retry count.
    """

    retry_count = state.get("retry_count", 0)
    max_results = settings.ARXIV_MAX_RESULTS

    if retry_count > 0:
        max_results = min(max_results + 2, 8)

    return max_results


def retrieve_by_query(query: str, state: AgentState) -> Dict[str, Any]:
    """
    Retrieve papers for a single query.

    This function keeps the original retrieval behavior:
    - use cache first
    - call arXiv if cache misses
    - use fallback papers if arXiv returns nothing
    """

    max_results = get_max_results(state)
    retrieval_mode = settings.RETRIEVAL_MODE.lower()

    papers: List[Dict[str, Any]] = []
    retrieval_source = retrieval_mode
    cache_hit = False
    tool_execution = {}

    if retrieval_mode == "arxiv":
        cached_papers = load_cached_papers(query)

        if cached_papers is not None:
            print(f"\n[Retrieve Node] Cache hit，使用本地缓存结果。query={query}")
            papers = cached_papers
            retrieval_source = "cache"
            cache_hit = True

        else:
            print(f"\n[Retrieve Node] Cache miss，调用 arXiv 检索。query={query}")

            tool_name = paper_tool_router.resolve(
                capability="paper.search",
                source="arxiv",
            )
            tool_result = paper_tool_executor.execute(
                tool_name=tool_name,
                arguments={
                    "query": query,
                    "max_results": max_results,
                },
            )
            tool_execution = {
                "tool_name": tool_result.tool_name,
                "tool_version": tool_result.tool_version,
                "tool_success": tool_result.success,
                "tool_error_code": tool_result.error_code,
                "tool_error_message": tool_result.error_message,
                "tool_latency_seconds": tool_result.latency_seconds,
                "tool_attempt_count": tool_result.attempt_count,
            }
            papers = (
                tool_result.data.get("papers", [])
                if tool_result.success and isinstance(tool_result.data, dict)
                else []
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

    tools_used = [f"{retrieval_source}_retriever"]
    tool_name = tool_execution.get("tool_name", "")
    if tool_name and tool_name not in tools_used:
        tools_used.append(tool_name)

    return {
        "documents": documents,
        "retrieval_source": retrieval_source,
        "retrieval_mode": retrieval_mode,
        "cache_hit": cache_hit,
        "search_query": query,
        "paper_count": len(documents),
        "tools_used": tools_used,
        "tool_execution": tool_execution,
    }


def retrieve_multi_query(state: AgentState, sub_queries: List[str]) -> AgentState:
    """
    Retrieve papers for multiple planned sub-queries and merge results.
    """

    document_groups: List[List[Dict[str, Any]]] = []
    retrieval_sources: List[str] = []
    tool_executions: List[Dict[str, Any]] = []
    search_queries: List[str] = []
    cache_hit_count = 0
    tools_used = list(state.get("tools_used", []))

    for sub_query in sub_queries:
        single_result = retrieve_by_query(sub_query, state)

        documents = single_result.get("documents", [])
        document_groups.append(documents)

        retrieval_source = single_result.get("retrieval_source", "")
        if retrieval_source:
            retrieval_sources.append(retrieval_source)

        search_query = single_result.get("search_query", "")
        if search_query:
            search_queries.append(search_query)

        if single_result.get("cache_hit", False):
            cache_hit_count += 1

        tool_execution = single_result.get("tool_execution", {})
        if tool_execution:
            tool_executions.append(tool_execution)

        for tool in single_result.get("tools_used", []):
            if tool not in tools_used:
                tools_used.append(tool)

    merge_result = merge_documents_with_stats(
        document_groups=document_groups,
        max_documents=settings.ARXIV_MAX_RESULTS,
    )

    documents = merge_result["documents"]

    if "agentic_rag_retriever" not in tools_used:
        tools_used.append("agentic_rag_retriever")

    return {
        "documents": documents,
        "tools_used": tools_used,
        "paper_metadata": {
            **state.get("paper_metadata", {}),
            "retrieval_source": "multi_query",
            "search_query": search_queries[0] if search_queries else "",
            "search_queries": search_queries,
            "paper_count": len(documents),
            "retrieval_count": len(documents),
            "retrieval_mode": settings.RETRIEVAL_MODE.lower(),
            "cache_hit": False,
            "cache_hit_count": cache_hit_count,
            "sub_queries": sub_queries,
            "sub_query_count": len(sub_queries),
            "raw_document_count": merge_result["raw_document_count"],
            "merged_document_count": merge_result["merged_document_count"],
            "deduplicated_count": merge_result["deduplicated_count"],
            "retrieval_sources": retrieval_sources,
            "agentic_rag_enabled": True,
            "tool_executions": tool_executions,
        },
    }


def retrieve_node(state: AgentState) -> AgentState:
    """
    Retrieve papers for the current AgentState.

    If sub_queries exist, use Agentic RAG multi-query retrieval.
    Otherwise, keep the original single-query retrieval behavior.
    """

    task_type = state.get("task_type", "qa")

    if task_type == "pdf_reading":
        return {
            "documents": [],
            "tools_used": state.get("tools_used", []),
            "paper_metadata": {
                **state.get("paper_metadata", {}),
                "retrieval_source": "pdf",
                "search_query": "",
                "paper_count": 0,
                "retrieval_count": 0,
                "retrieval_mode": "pdf",
                "cache_hit": False,
                "is_pdf_task": True,
            },
        }

    paper_metadata = state.get("paper_metadata", {})
    sub_queries = state.get("sub_queries") or paper_metadata.get("sub_queries", [])

    if len(sub_queries) > 1:
        return retrieve_multi_query(state, sub_queries)

    query = (
        sub_queries[0]
        if sub_queries
        else state.get("rewritten_query") or state.get("query", "")
    )

    single_result = retrieve_by_query(query, state)
    documents = single_result.get("documents", [])

    tools_used = list(state.get("tools_used", []))
    for tool in single_result.get("tools_used", []):
        if tool not in tools_used:
            tools_used.append(tool)

    return {
        "documents": documents,
        "tools_used": tools_used,
        "paper_metadata": {
            **state.get("paper_metadata", {}),
            "retrieval_source": single_result.get("retrieval_source", ""),
            "search_query": query,
            "paper_count": len(documents),
            "retrieval_count": len(documents),
            "retrieval_mode": single_result.get("retrieval_mode", settings.RETRIEVAL_MODE.lower()),
            "cache_hit": single_result.get("cache_hit", False),
            "agentic_rag_enabled": False,
            "tool_executions": (
                [single_result["tool_execution"]]
                if single_result.get("tool_execution")
                else []
            ),
        },
    }
