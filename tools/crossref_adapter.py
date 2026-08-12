"""Crossref DOI authority lookup behind PaperAgent's stable tool protocol."""

from pydantic import BaseModel

from core.config import settings
from tools.contracts import RetryPolicy, ToolRiskLevel, ToolSpec
from tools.crossref_client import CrossrefClient
from tools.paper_models import PaperLookupInput, PaperLookupOutput


class CrossrefLookupTool:
    spec = ToolSpec(
        name="paper.lookup.crossref",
        version="1.0.0",
        description="Look up canonical publication metadata by DOI.",
        input_model=PaperLookupInput,
        output_model=PaperLookupOutput,
        provider="crossref",
        capabilities=("paper.lookup",),
        risk_level=ToolRiskLevel.READ_ONLY,
        timeout_seconds=settings.TOOL_TIMEOUT_SECONDS,
        retry_policy=RetryPolicy(max_attempts=2),
        cache_policy="external",
    )

    def __init__(self, client: CrossrefClient | None = None) -> None:
        self.client = client or CrossrefClient(
            settings.CROSSREF_BASE_URL,
            settings.CROSSREF_MAILTO,
            settings.TOOL_TIMEOUT_SECONDS,
        )

    def invoke(self, arguments: BaseModel):
        request = PaperLookupInput.model_validate(arguments)
        return {"paper": self.client.lookup_work(request.identity)}
