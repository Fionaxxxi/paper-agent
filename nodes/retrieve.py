import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List

from agent.state import AgentState
from core.config import settings
from retrieval.cache import load_cached_papers, save_cached_papers
from retrieval.metadata_resolver import extract_arxiv_ids, normalize_doi
from retrieval.reranker import rerank_documents_with_stats
from retrieval.result_merger import merge_documents_with_stats
from tools.contracts import ToolErrorCode
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


def load_arxiv_authority_evidence(
    document_groups: List[List[Dict[str, Any]]],
) -> tuple[dict[str, Dict[str, Any]], list[dict[str, Any]], list[str]]:
    """Resolve secondary arXiv claims with success-only persistent caching."""

    native_ids = {
        arxiv_id
        for group in document_groups
        for document in group
        if str(document.get("source") or "").casefold() == "arxiv"
        for arxiv_id in extract_arxiv_ids(document)
    }
    claimed_ids = {
        arxiv_id
        for group in document_groups
        for document in group
        if str(document.get("source") or "").casefold() != "arxiv"
        for arxiv_id in extract_arxiv_ids(document)
    } - native_ids
    authority = {}
    executions = []
    tools_used = []
    tool_name = paper_tool_router.resolve("paper.lookup", "arxiv")
    cache_dir = Path(settings.CACHE_DIR) / "authority" / "arxiv"
    for arxiv_id in sorted(claimed_ids):
        cache_path = cache_dir / f"{arxiv_id}.json"
        if cache_path.exists():
            authority[f"arxiv:{arxiv_id}"] = json.loads(
                cache_path.read_text(encoding="utf-8")
            )
            continue
        result = paper_tool_executor.execute(tool_name, {"identity": arxiv_id})
        executions.append(_tool_execution_metadata(result))
        if tool_name not in tools_used:
            tools_used.append(tool_name)
        if not result.success:
            continue
        paper = result.data.get("paper") if isinstance(result.data, dict) else None
        evidence = paper or {
            "source": "arxiv_authority",
            "canonical_identity": f"arxiv:{arxiv_id}",
            "canonical_lookup_status": "NOT_FOUND",
        }
        authority[f"arxiv:{arxiv_id}"] = evidence
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(
            json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return authority, executions, tools_used


def load_doi_authority_evidence(
    document_groups: List[List[Dict[str, Any]]],
) -> tuple[dict[str, Dict[str, Any]], list[dict[str, Any]], list[str]]:
    """Resolve ordinary DOI claims through Crossref with success-only caching."""

    claimed_dois = {
        doi
        for group in document_groups
        for document in group
        if (doi := normalize_doi(document.get("doi")))
        and not doi.startswith("10.48550/arxiv.")
    }
    authority = {}
    executions = []
    tools_used = []
    tool_name = paper_tool_router.resolve("paper.lookup", "crossref")
    cache_dir = Path(settings.CACHE_DIR) / "authority" / "crossref"
    for doi in sorted(claimed_dois):
        cache_path = cache_dir / f"{doi.replace('/', '__')}.json"
        if cache_path.exists():
            authority[f"doi:{doi}"] = json.loads(
                cache_path.read_text(encoding="utf-8")
            )
            continue
        result = paper_tool_executor.execute(tool_name, {"identity": doi})
        executions.append(_tool_execution_metadata(result))
        if tool_name not in tools_used:
            tools_used.append(tool_name)
        if not result.success:
            continue
        paper = result.data.get("paper") if isinstance(result.data, dict) else None
        evidence = paper or {
            "source": "crossref",
            "canonical_identity": f"doi:{doi}",
            "canonical_lookup_status": "NOT_FOUND",
        }
        authority[f"doi:{doi}"] = evidence
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(
            json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    return authority, executions, tools_used


def convert_papers_to_documents(papers: List[Dict[str, Any]], source: str) -> List[Dict[str, Any]]:
    documents = []

    for paper in papers:
        documents.append(
            {
                "title": paper.get("title"),
                "authors": paper.get("authors", []),
                "year": paper.get("year"),
                "content": (
                    paper.get("summary")
                    or paper.get("content")
                    or paper.get("abstract")
                    or "；".join(paper.get("notes", []))
                    or "；".join(paper.get("dimensions", []))
                ),
                "pdf_url": paper.get("pdf_url"),
                "entry_id": paper.get("entry_id") or paper.get("arxiv_id") or paper.get("item_key"),
                "doi": paper.get("doi", ""),
                "cited_by_count": paper.get("cited_by_count", 0),
                "landing_page_url": paper.get("landing_page_url", ""),
                "source": paper.get("source", source),
                "document_id": paper.get("document_id", ""),
                "catalog_group": paper.get("group", ""),
                "tags": paper.get("tags", []),
                "collection_keys": paper.get("collection_keys", []),
                "notes": paper.get("notes", []),
                "pdf_attachment_keys": paper.get("pdf_attachment_keys", []),
            }
        )

    return documents


def get_max_results(state: AgentState, source: str = "arxiv") -> int:
    """
    Decide max retrieval results according to retry count.
    """

    retry_count = state.get("retry_count", 0)
    max_results = (
        settings.OPENALEX_MAX_RESULTS
        if source == "openalex"
        else (
            settings.ZOTERO_MAX_RESULTS
            if source == "zotero"
            else settings.LOCAL_RAG_MAX_RESULTS
            if source == "mcp_catalog"
            else settings.ARXIV_MAX_RESULTS
        )
    )

    if retry_count > 0:
        max_results = min(max_results + 2, 8)

    return max_results


def get_retrieval_sources(retrieval_mode: str) -> List[str]:
    """Resolve configured native providers without changing the default mode."""

    if retrieval_mode in {"arxiv", "openalex", "mcp_catalog", "zotero"}:
        return [retrieval_mode]
    if retrieval_mode in {"multi", "multi_source"}:
        return [
            source.strip().lower()
            for source in settings.MULTI_SOURCE_PROVIDERS.split(",")
            if source.strip()
        ]
    return []


def _tool_execution_metadata(tool_result) -> Dict[str, Any]:
    return {
        "tool_name": tool_result.tool_name,
        "tool_version": tool_result.tool_version,
        "tool_success": tool_result.success,
        "tool_error_code": tool_result.error_code,
        "tool_error_message": tool_result.error_message,
        "tool_latency_seconds": tool_result.latency_seconds,
        "tool_attempt_count": tool_result.attempt_count,
        "tool_source": tool_result.source,
        "tool_metadata": dict(tool_result.metadata),
    }


def retrieve_from_source(
    query: str,
    state: AgentState,
    source: str,
) -> Dict[str, Any]:
    """Retrieve one query from one provider with a source-scoped cache."""

    cached_papers = load_cached_papers(query, source=source)
    if cached_papers is not None:
        return {
            "papers": cached_papers,
            "provider": source,
            "retrieval_source": "cache",
            "cache_hit": True,
            "tools_used": [f"{source}_cache_retriever"],
            "tool_execution": {},
        }

    try:
        capability = (
            "paper.catalog.search"
            if source == "mcp_catalog"
            else "library.search"
            if source == "zotero"
            else "paper.search"
        )
        tool_name = paper_tool_router.resolve(capability=capability, source=source)
    except KeyError as error:
        return {
            "papers": [],
            "provider": source,
            "retrieval_source": source,
            "cache_hit": False,
            "tools_used": [],
            "tool_execution": {
                "tool_name": "",
                "tool_version": "",
                "tool_success": False,
                "tool_error_code": ToolErrorCode.TOOL_NOT_FOUND.value,
                "tool_error_message": str(error),
                "tool_latency_seconds": 0.0,
                "tool_attempt_count": 0,
                "tool_route": {
                    "capability": (
                        "paper.catalog.search"
                        if source == "mcp_catalog"
                        else "library.search"
                        if source == "zotero"
                        else "paper.search"
                    ),
                    "source": source,
                },
            },
        }

    arguments = (
        {"query": query, "limit": get_max_results(state, source)}
        if source in {"mcp_catalog", "zotero"}
        else {"query": query, "max_results": get_max_results(state, source)}
    )
    tool_result = paper_tool_executor.execute(
        tool_name=tool_name,
        arguments=arguments,
    )
    papers = (
        tool_result.data.get("items" if source == "zotero" else "papers", [])
        if tool_result.success and isinstance(tool_result.data, dict)
        else []
    )
    if papers:
        save_cached_papers(query, papers, source=source)

    return {
        "papers": papers,
        "provider": source,
        "retrieval_source": source,
        "cache_hit": False,
        "tools_used": [f"{source}_retriever", tool_name],
        "tool_execution": {
            **_tool_execution_metadata(tool_result),
            "tool_route": {
                "capability": capability,
                "source": source,
                "tool_name": tool_name,
            },
        },
    }


def retrieve_by_query(query: str, state: AgentState) -> Dict[str, Any]:
    """Retrieve one query from the configured single or multiple providers."""

    retrieval_mode = settings.RETRIEVAL_MODE.lower()
    if retrieval_mode == "local_rag":
        from local_rag.runtime import search_local_papers

        local_result = search_local_papers(query, settings.LOCAL_RAG_MAX_RESULTS)
        documents = local_result["documents"]
        decision = local_result["decision"]
        return {
            "documents": documents,
            "retrieval_source": "local_rag",
            "retrieval_mode": retrieval_mode,
            "cache_hit": True,
            "search_query": query,
            "paper_count": len(documents),
            "tools_used": ["local_rag_retriever", f"local_rag_{decision.get('route', 'dense')}"],
            "tool_execution": {},
            "tool_executions": [],
            "source_statuses": [{"provider":"local_rag","retrieval_source":"local_rag","cache_hit":True,"paper_count":len(documents)}],
            "cache_hit_count": 1,
            "raw_document_count": len(documents),
            "merged_document_count": len(documents),
            "deduplicated_count": 0,
            "candidate_count_before_top_k": len(documents),
            "metadata_warning_count": 0,
            "metadata_repaired_count": 0,
            "metadata_quarantined_count": 0,
            "ranking_strategy": "confidence_gated_bm25_dense_rrf",
            "local_rag_decision": decision,
        }
    sources = get_retrieval_sources(retrieval_mode)
    if settings.MULTI_SOURCE_PARALLEL_ENABLED and len(sources) > 1:
        worker_count = max(1, min(settings.MULTI_SOURCE_MAX_WORKERS, len(sources)))
        with ThreadPoolExecutor(max_workers=worker_count) as pool:
            futures = [
                pool.submit(retrieve_from_source, query, state, source)
                for source in sources
            ]
            source_results = [future.result() for future in futures]
    else:
        source_results = [
            retrieve_from_source(query, state, source)
            for source in sources
        ]

    document_groups = [
        convert_papers_to_documents(result["papers"], result["provider"])
        for result in source_results
        if result["papers"]
    ]
    tool_executions = [
        result["tool_execution"]
        for result in source_results
        if result["tool_execution"]
    ]
    tools_used = []
    for result in source_results:
        for tool in result["tools_used"]:
            if tool and tool not in tools_used:
                tools_used.append(tool)

    if document_groups:
        max_documents = (
            settings.MULTI_SOURCE_MAX_RESULTS
            if len(sources) > 1
            else get_max_results(state, sources[0])
        )
        if len(sources) > 1 and settings.MULTI_SOURCE_RERANK_ENABLED:
            authority_by_identity = {}
            if settings.ARXIV_AUTHORITY_VERIFICATION_ENABLED:
                arxiv_authority, authority_executions, authority_tools = (
                    load_arxiv_authority_evidence(document_groups)
                )
                authority_by_identity.update(arxiv_authority)
                tool_executions.extend(authority_executions)
                for tool in authority_tools:
                    if tool not in tools_used:
                        tools_used.append(tool)
            if settings.DOI_AUTHORITY_VERIFICATION_ENABLED:
                doi_authority, authority_executions, authority_tools = (
                    load_doi_authority_evidence(document_groups)
                )
                authority_by_identity.update(doi_authority)
                tool_executions.extend(authority_executions)
                for tool in authority_tools:
                    if tool not in tools_used:
                        tools_used.append(tool)
            merge_result = rerank_documents_with_stats(
                query=query,
                document_groups=document_groups,
                max_documents=max_documents,
                metadata_resolution_enabled=(
                    settings.MULTI_SOURCE_METADATA_VERIFICATION_ENABLED
                    or settings.ARXIV_AUTHORITY_VERIFICATION_ENABLED
                    or settings.DOI_AUTHORITY_VERIFICATION_ENABLED
                ),
                authority_by_identity=authority_by_identity or None,
            )
        else:
            merge_result = merge_documents_with_stats(
                document_groups=document_groups,
                max_documents=max_documents,
            )
        documents = merge_result["documents"]
        if len(sources) > 1:
            retrieval_source = "multi_source"
        else:
            retrieval_source = source_results[0]["retrieval_source"]
    else:
        documents = (
            []
            if retrieval_mode == "zotero"
            else convert_papers_to_documents(FALLBACK_PAPERS, "fallback")
        )
        retrieval_source = "zotero" if retrieval_mode == "zotero" else "fallback"
        merge_result = {
            "raw_document_count": 0,
            "merged_document_count": len(documents),
            "deduplicated_count": 0,
        }
        if retrieval_mode != "zotero" and "fallback_retriever" not in tools_used:
            tools_used.append("fallback_retriever")

    cache_hit_count = sum(result["cache_hit"] for result in source_results)
    cache_hit = bool(source_results) and cache_hit_count == len(source_results)
    source_statuses = [
        {
            "provider": result["provider"],
            "retrieval_source": result["retrieval_source"],
            "cache_hit": result["cache_hit"],
            "paper_count": len(result["papers"]),
        }
        for result in source_results
    ]

    return {
        "documents": documents,
        "retrieval_source": retrieval_source,
        "retrieval_mode": retrieval_mode,
        "cache_hit": cache_hit,
        "search_query": query,
        "paper_count": len(documents),
        "tools_used": tools_used,
        "tool_execution": tool_executions[0] if tool_executions else {},
        "tool_executions": tool_executions,
        "source_statuses": source_statuses,
        "cache_hit_count": cache_hit_count,
        "raw_document_count": merge_result["raw_document_count"],
        "merged_document_count": merge_result["merged_document_count"],
        "deduplicated_count": merge_result["deduplicated_count"],
        "candidate_count_before_top_k": merge_result.get(
            "candidate_count_before_top_k",
            merge_result["merged_document_count"],
        ),
        "metadata_warning_count": merge_result.get("metadata_warning_count", 0),
        "metadata_repaired_count": merge_result.get("metadata_repaired_count", 0),
        "metadata_quarantined_count": merge_result.get(
            "metadata_quarantined_count", 0
        ),
        "ranking_strategy": merge_result.get("ranking_strategy", "source_priority"),
    }


def retrieve_multi_query(state: AgentState, sub_queries: List[str]) -> AgentState:
    """
    Retrieve papers for multiple planned sub-queries and merge results.
    """

    document_groups: List[List[Dict[str, Any]]] = []
    retrieval_sources: List[str] = []
    source_statuses: List[Dict[str, Any]] = []
    tool_executions: List[Dict[str, Any]] = []
    search_queries: List[str] = []
    cache_hit_count = 0
    tools_used = list(state.get("tools_used", []))

    if settings.MULTI_QUERY_PARALLEL_ENABLED and len(sub_queries) > 1:
        worker_count = max(1, min(settings.MULTI_QUERY_MAX_WORKERS, len(sub_queries)))
        with ThreadPoolExecutor(max_workers=worker_count) as pool:
            futures = [
                pool.submit(retrieve_by_query, sub_query, state)
                for sub_query in sub_queries
            ]
            query_results = [future.result() for future in futures]
    else:
        query_results = [
            retrieve_by_query(sub_query, state) for sub_query in sub_queries
        ]

    for single_result in query_results:

        documents = single_result.get("documents", [])
        document_groups.append(documents)

        retrieval_source = single_result.get("retrieval_source", "")
        if retrieval_source:
            retrieval_sources.append(retrieval_source)

        search_query = single_result.get("search_query", "")
        if search_query:
            search_queries.append(search_query)

        cache_hit_count += single_result.get(
            "cache_hit_count",
            int(single_result.get("cache_hit", False)),
        )

        source_statuses.extend(single_result.get("source_statuses", []))

        tool_executions.extend(single_result.get("tool_executions", []))

        for tool in single_result.get("tools_used", []):
            if tool not in tools_used:
                tools_used.append(tool)

    merge_result = merge_documents_with_stats(
        document_groups=document_groups,
        max_documents=(
            settings.MULTI_SOURCE_MAX_RESULTS
            if settings.RETRIEVAL_MODE.lower() in {"multi", "multi_source"}
            else settings.ARXIV_MAX_RESULTS
        ),
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
            "source_statuses": source_statuses,
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

    if len(sub_queries) > 1 and not state.get("retry_query"):
        return retrieve_multi_query(state, sub_queries)

    query = (
        state.get("retry_query")
        or (sub_queries[0] if sub_queries else "")
        or state.get("rewritten_query")
        or state.get("query", "")
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
            "tool_executions": single_result.get("tool_executions", []),
            "source_statuses": single_result.get("source_statuses", []),
            "raw_document_count": single_result.get("raw_document_count", len(documents)),
            "merged_document_count": single_result.get("merged_document_count", len(documents)),
            "deduplicated_count": single_result.get("deduplicated_count", 0),
            "ranking_strategy": single_result.get("ranking_strategy", "source_priority"),
            "local_rag_decision": single_result.get("local_rag_decision", {}),
        },
    }
