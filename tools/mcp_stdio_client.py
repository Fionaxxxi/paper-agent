"""官方 MCP SDK stdio Client 的同步薄封装。"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class StdioMCPClient:
    command: str
    args: tuple[str, ...]
    cwd: str | None = None
    env: dict[str, str] | None = field(default=None)

    def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        return asyncio.run(self._call_tool(name, arguments))

    async def _call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        from mcp import Client, StdioServerParameters
        from mcp.client.stdio import stdio_client

        parameters = StdioServerParameters(
            command=self.command,
            args=list(self.args),
            cwd=self.cwd,
            env=self.env,
        )
        async with Client(stdio_client(parameters)) as client:
            return await client.call_tool(name, arguments)
