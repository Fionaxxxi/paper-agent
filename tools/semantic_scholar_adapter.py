"""Semantic Scholar DOI authority lookup behind PaperAgent's tool protocol."""

from pydantic import BaseModel

from core.config import settings
from tools.contracts import RetryPolicy, ToolRiskLevel, ToolSpec
from tools.paper_models import PaperLookupInput, PaperLookupOutput
from tools.semantic_scholar_client import SemanticScholarClient


class SemanticScholarLookupTool:
    spec = ToolSpec(
        name="paper.lookup.semantic_scholar",
        version="1.0.0",
        description="Look up scholarly metadata by DOI through Semantic Scholar.",
        input_model=PaperLookupInput,
        output_model=PaperLookupOutput,
        provider="semantic_scholar",
        capabilities=("paper.lookup",),
        risk_level=ToolRiskLevel.READ_ONLY,
        timeout_seconds=settings.TOOL_TIMEOUT_SECONDS,
        retry_policy=RetryPolicy(max_attempts=2),
        cache_policy="external",
    )

    def __init__(self, client: SemanticScholarClient | None = None) -> None:
        self.client = client or SemanticScholarClient(
            settings.SEMANTIC_SCHOLAR_BASE_URL,
            settings.SEMANTIC_SCHOLAR_API_KEY,
            settings.TOOL_TIMEOUT_SECONDS,
        )

    def invoke(self, arguments: BaseModel):
        request = PaperLookupInput.model_validate(arguments)
        return {"paper": self.client.lookup_paper(request.identity)}
