"""Zotero 只读 MCP 工具的 PaperAgent 注册定义。"""

from __future__ import annotations

import sys
from pathlib import Path

from pydantic import BaseModel, Field

from tools.contracts import RetryPolicy, ToolRiskLevel, ToolSpec
from tools.mcp_adapter import MCPServerIdentity, MCPToolAdapter
from tools.mcp_stdio_client import StdioMCPClient


class ZoteroSearchInput(BaseModel):
    query: str = Field(default="", max_length=500)
    tag: str = Field(default="", max_length=200)
    collection_key: str = Field(default="", pattern=r"^[A-Za-z0-9]*$")
    limit: int = Field(default=5, ge=1, le=20)
    include_notes: bool = True


class ZoteroLibraryItem(BaseModel):
    item_key: str
    item_type: str = ""
    title: str = ""
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    abstract: str = ""
    doi: str = ""
    url: str = ""
    tags: list[str] = Field(default_factory=list)
    collection_keys: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    pdf_attachment_keys: list[str] = Field(default_factory=list)


class ZoteroSearchOutput(BaseModel):
    items: list[ZoteroLibraryItem] = Field(default_factory=list)
    total_matches: int = Field(ge=0)


def build_zotero_mcp_tool() -> MCPToolAdapter:
    root = Path(__file__).resolve().parents[1]
    return MCPToolAdapter(
        client=StdioMCPClient(
            command=sys.executable,
            args=("-m", "mcp_servers.zotero_server"),
            cwd=str(root),
        ),
        remote_tool_name="search_library",
        spec=ToolSpec(
            name="library.search.zotero.mcp",
            version="1.0.0",
            description="通过只读 MCP Server 搜索 Zotero 文献库、标签和笔记。",
            input_model=ZoteroSearchInput,
            output_model=ZoteroSearchOutput,
            provider="zotero_mcp",
            capabilities=("library.search",),
            risk_level=ToolRiskLevel.READ_ONLY,
            timeout_seconds=45,
            retry_policy=RetryPolicy(max_attempts=1),
            cache_policy="none",
        ),
        server=MCPServerIdentity("paperagent-zotero", "1.0.0", "stdio"),
    )
