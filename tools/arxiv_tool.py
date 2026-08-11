from typing import List, Dict, Any
import arxiv


def _serialize_arxiv_result(result) -> Dict[str, Any]:
    return {
        "title": result.title,
        "authors": [author.name for author in result.authors],
        "year": result.published.year,
        "summary": result.summary,
        "pdf_url": result.pdf_url,
        "entry_id": result.entry_id,
        "doi": result.doi or "",
        "cited_by_count": 0,
        "landing_page_url": result.entry_id,
        "source": "arxiv",
    }


def search_arxiv_papers(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Search papers from arXiv.

    Network failures are re-raised so ToolExecutor can record a structured
    failure; Retrieve Node remains responsible for fallback behavior.
    """
    try:
        client = arxiv.Client(
            page_size=max_results,
            delay_seconds=3,
            num_retries=2,
        )

        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance,
            sort_order=arxiv.SortOrder.Descending,
        )

        papers = []

        for result in client.results(search):
            papers.append(_serialize_arxiv_result(result))

            if len(papers) >= max_results:
                break

        return papers

    except Exception as e:
        print("\n[arXiv Tool Error] arXiv 检索失败：")
        print(e)
        raise


def lookup_arxiv_paper(arxiv_id: str) -> Dict[str, Any] | None:
    """Look up one canonical arXiv record by native identifier."""

    client = arxiv.Client(page_size=1, delay_seconds=3, num_retries=2)
    search = arxiv.Search(id_list=[arxiv_id], max_results=1)
    result = next(iter(client.results(search)), None)
    return _serialize_arxiv_result(result) if result is not None else None

    # 1. 设置 page_size，避免默认请求 100 条
    # 2. 捕获 arXiv / SSL / 网络异常
    # 3. 网络失败交给 ToolExecutor 统一记录，Retrieve Node 再执行降级
