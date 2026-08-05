"""Native arXiv implementation behind the stable PaperAgent tool protocol."""

from __future__ import annotations

from pydantic import BaseModel

from core.config import settings
from tools.arxiv_tool import search_arxiv_papers
from tools.contracts import RetryPolicy, ToolRiskLevel, ToolSpec
from tools.paper_models import PaperSearchInput, PaperSearchOutput


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
