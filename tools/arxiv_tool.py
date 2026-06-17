from typing import List, Dict, Any
import arxiv


def search_arxiv_papers(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    client = arxiv.Client()

    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance,
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

    return papers