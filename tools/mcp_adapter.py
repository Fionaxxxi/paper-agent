"""将 MCP Client 暴露的远程工具适配到 PaperAgent 统一工具协议。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from pydantic import BaseModel

from tools.contracts import ToolSpec


class MCPClient(Protocol):
    """传输无关的最小 MCP Client 契约。"""

    def call_tool(self, name: str, arguments: dict[str, Any]) -> Any: ...


@dataclass(frozen=True)
class MCPServerIdentity:
    name: str
    version: str = "unknown"
    transport: str = "unknown"


class MCPToolAdapter:
    """让只读 MCP 工具复用 Registry、Policy、Executor 与 ToolResult。"""

    def __init__(
        self,
        client: MCPClient,
        remote_tool_name: str,
        spec: ToolSpec,
        server: MCPServerIdentity,
    ) -> None:
        self.client = client
        self.remote_tool_name = remote_tool_name
        self.spec = spec
        self.server = server

    def invoke(self, arguments: BaseModel) -> Any:
        result = self.client.call_tool(
            self.remote_tool_name,
            arguments.model_dump(mode="python", exclude_none=True),
        )
        return self._unwrap(result)

    @staticmethod
    def _unwrap(result: Any) -> Any:
        """兼容直接结构化数据和 MCP SDK 常见 structuredContent 包装。"""
        if isinstance(result, dict):
            if result.get("isError") is True or result.get("is_error") is True:
                raise RuntimeError(str(result.get("error") or result.get("content") or "MCP tool failed"))
            if "structuredContent" in result:
                return result["structuredContent"]
            if "structured_content" in result:
                return result["structured_content"]
        if getattr(result, "isError", False) is True or getattr(result, "is_error", False) is True:
            content = getattr(result, "content", None) or []
            message = " ".join(str(getattr(item, "text", item)) for item in content)
            raise RuntimeError(message or "MCP tool failed")
        structured = getattr(result, "structuredContent", None)
        if structured is None:
            structured = getattr(result, "structured_content", None)
        return structured if structured is not None else result

    @property
    def audit_metadata(self) -> dict[str, str]:
        return {
            "tool_origin": "mcp",
            "mcp_server": self.server.name,
            "mcp_server_version": self.server.version,
            "mcp_transport": self.server.transport,
            "mcp_remote_tool": self.remote_tool_name,
        }
