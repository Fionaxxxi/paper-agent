"""Native arXiv implementation behind the stable PaperAgent tool protocol."""

from __future__ import annotations

from pydantic import BaseModel

from core.config import settings
from tools.arxiv_tool import lookup_arxiv_paper, search_arxiv_papers
from tools.contracts import RetryPolicy, ToolRiskLevel, ToolSpec
from tools.paper_models import (
    PaperLookupInput,
    PaperLookupOutput,
    PaperSearchInput,
    PaperSearchOutput,
)


class ArxivSearchTool:
    spec = ToolSpec(
        name="paper.search.arxiv",
        version="1.0.0",
        description="Search arXiv for academic papers.",
        input_model=PaperSearchInput,
        output_model=PaperSearchOutput,
        provider="arxiv",
        capabilities=("paper.search",),
        risk_level=ToolRiskLevel.READ_ONLY,
        timeout_seconds=settings.TOOL_TIMEOUT_SECONDS,
        # The arxiv client already performs its own bounded retries.
        retry_policy=RetryPolicy(max_attempts=1),
        cache_policy="external",
    )

    def invoke(self, arguments: BaseModel):
        request = PaperSearchInput.model_validate(arguments)
        return {
            "papers": search_arxiv_papers(
                query=request.query,
                max_results=request.max_results,
            )
        }


class ArxivLookupTool:
    spec = ToolSpec(
        name="paper.lookup.arxiv",
        version="1.0.0",
        description="Look up canonical arXiv metadata by native identifier.",
        input_model=PaperLookupInput,
        output_model=PaperLookupOutput,
        provider="arxiv",
        capabilities=("paper.lookup",),
        risk_level=ToolRiskLevel.READ_ONLY,
        timeout_seconds=settings.TOOL_TIMEOUT_SECONDS,
        retry_policy=RetryPolicy(max_attempts=1),
        cache_policy="external",
    )

    def invoke(self, arguments: BaseModel):
        request = PaperLookupInput.model_validate(arguments)
        return {"paper": lookup_arxiv_paper(request.identity)}
