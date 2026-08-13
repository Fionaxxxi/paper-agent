"""通过 MCP stdio 暴露本地代表论文目录，只读且不访问网络。"""

from __future__ import annotations

import json
from pathlib import Path

from mcp.server import MCPServer
from pydantic import BaseModel


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "papers" / "corpus_sources.json"
mcp = MCPServer(
    "paperagent-corpus",
    version="1.0.0",
    instructions="只读查询 PaperAgent 本地代表论文目录。",
)


class CatalogPaper(BaseModel):
    document_id: str
    title: str
    arxiv_id: str
    group: str
    dimensions: list[str]
    pdf_url: str = ""


class CatalogSearchResult(BaseModel):
    papers: list[CatalogPaper]
    total_matches: int


def _documents() -> list[dict]:
    return json.loads(CATALOG.read_text(encoding="utf-8"))["documents"]


@mcp.tool(annotations={"readOnlyHint": True}, structured_output=True)
def search_corpus(query: str = "", limit: int = 5) -> CatalogSearchResult:
    """按标题、分组、研究维度和 arXiv ID 查询本地论文目录。"""
    if limit < 1 or limit > 20:
        raise ValueError("limit 必须在 1 到 20 之间")
    terms = [term.casefold() for term in query.split() if term.strip()]
    matches = []
    for document in _documents():
        searchable = " ".join([
            document.get("title", ""), document.get("group", ""),
            document.get("arxiv_id", ""), " ".join(document.get("dimensions", [])),
        ]).casefold()
        if not terms or all(term in searchable for term in terms):
            matches.append(CatalogPaper(**{
                "document_id": document["document_id"],
                "title": document["title"],
                "arxiv_id": document["arxiv_id"],
                "group": document["group"],
                "dimensions": document.get("dimensions", []),
                "pdf_url": document.get("pdf_url", ""),
            }))
    return CatalogSearchResult(papers=matches[:limit], total_matches=len(matches))


@mcp.resource("paperagent://corpus/catalog", mime_type="application/json")
def corpus_catalog() -> str:
    """返回完整、只读的本地代表论文目录。"""
    return CATALOG.read_text(encoding="utf-8")


if __name__ == "__main__":
    mcp.run(transport="stdio")
