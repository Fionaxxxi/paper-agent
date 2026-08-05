"""Base protocol for executable PaperAgent tools."""

from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel

from tools.contracts import ToolSpec


class Tool(Protocol):
    spec: ToolSpec

    def invoke(self, arguments: BaseModel) -> Any:
        """Execute the tool with already validated arguments."""
