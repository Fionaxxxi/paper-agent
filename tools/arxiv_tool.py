from typing import List, Dict, Any
import arxiv


def search_arxiv_papers(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Search papers from arXiv.

    If arXiv network request fails, return an empty list instead of crashing
    the whole LangGraph workflow.
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
            papers.append(
                {
                    "title": result.title,
                    "authors": [author.name for author in result.authors],
                    "year": result.published.year,
                    "summary": result.summary,
                    "pdf_url": result.pdf_url,
                    "entry_id": result.entry_id,
                    "source": "arxiv",
                }
            )

            if len(papers) >= max_results:
                break

        return papers

    except Exception as e:
        print("\n[arXiv Tool Error] arXiv 检索失败：")
        print(e)
        return []

    # 1. 设置 page_size，避免默认请求 100 条
    # 2. 捕获 arXiv / SSL / 网络异常
    # 3. 网络失败时返回空列表，不让整个程序崩溃