"""真实本地 MCP 论文目录工具的 PaperAgent 注册定义。"""

from __future__ import annotations

import sys
from pathlib import Path

from pydantic import BaseModel, Field

from tools.contracts import RetryPolicy, ToolRiskLevel, ToolSpec
from tools.mcp_adapter import MCPServerIdentity, MCPToolAdapter
from tools.mcp_stdio_client import StdioMCPClient


class CorpusSearchInput(BaseModel):
    query: str = ""
    limit: int = Field(default=5, ge=1, le=20)


class CorpusPaper(BaseModel):
    document_id: str
    title: str
    arxiv_id: str
    group: str
    dimensions: list[str]
    pdf_url: str = ""


class CorpusSearchOutput(BaseModel):
    papers: list[CorpusPaper]
    total_matches: int = Field(ge=0)


def build_paper_catalog_mcp_tool() -> MCPToolAdapter:
    root = Path(__file__).resolve().parents[1]
    return MCPToolAdapter(
        client=StdioMCPClient(
            command=sys.executable,
            args=("-m", "mcp_servers.paper_catalog_server"),
            cwd=str(root),
        ),
        remote_tool_name="search_corpus",
        spec=ToolSpec(
            name="paper.catalog.search.mcp",
            version="1.0.0",
            description="通过只读 MCP Server 查询 PaperAgent 本地论文目录。",
            input_model=CorpusSearchInput,
            output_model=CorpusSearchOutput,
            provider="paperagent_corpus_mcp",
            capabilities=("paper.catalog.search",),
            risk_level=ToolRiskLevel.READ_ONLY,
            timeout_seconds=15,
            retry_policy=RetryPolicy(max_attempts=1),
            cache_policy="none",
        ),
        server=MCPServerIdentity("paperagent-corpus", "1.0.0", "stdio"),
    )
