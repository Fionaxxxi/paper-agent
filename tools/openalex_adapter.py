"""OpenAlex implementation behind PaperAgent's stable tool protocol."""

from __future__ import annotations

from pydantic import BaseModel

from core.config import settings
from tools.contracts import RetryPolicy, ToolRiskLevel, ToolSpec
from tools.openalex_client import OpenAlexClient
from tools.paper_models import PaperSearchInput, PaperSearchOutput


class OpenAlexSearchTool:
    spec = ToolSpec(
        name="paper.search.openalex",
        version="1.0.0",
        description="Search OpenAlex for academic works.",
        input_model=PaperSearchInput,
        output_model=PaperSearchOutput,
        provider="openalex",
        capabilities=("paper.search",),
        risk_level=ToolRiskLevel.READ_ONLY,
        timeout_seconds=settings.TOOL_TIMEOUT_SECONDS,
        retry_policy=RetryPolicy(max_attempts=2),
        cache_policy="external",
    )

    def __init__(self, client: OpenAlexClient | None = None) -> None:
        self.client = client or OpenAlexClient(
            base_url=settings.OPENALEX_BASE_URL,
            api_key=settings.OPENALEX_API_KEY,
            mailto=settings.OPENALEX_MAILTO,
            timeout_seconds=settings.TOOL_TIMEOUT_SECONDS,
        )

    def invoke(self, arguments: BaseModel):
        request = PaperSearchInput.model_validate(arguments)
        return {
            "papers": self.client.search_works(
                query=request.query,
                max_results=request.max_results,
            )
        }
