"""通过 MCP stdio 暴露 Zotero 个人/群组文献库的只读搜索。"""

from mcp.server import MCPServer

from core.config import settings
from tools.mcp_zotero import ZoteroSearchOutput
from tools.zotero_client import ZoteroReadOnlyClient


mcp = MCPServer(
    "paperagent-zotero",
    version="1.0.0",
    instructions="只读搜索 Zotero 文献库；不提供新增、修改或删除能力。",
)


@mcp.tool(annotations={"readOnlyHint": True}, structured_output=True)
def search_library(
    query: str = "",
    tag: str = "",
    collection_key: str = "",
    limit: int = 5,
    include_notes: bool = True,
) -> ZoteroSearchOutput:
    """搜索 Zotero 顶层文献，并按需返回子笔记和 PDF 附件标识。"""
    client = ZoteroReadOnlyClient(
        base_url=settings.ZOTERO_API_BASE_URL,
        library_type=settings.ZOTERO_LIBRARY_TYPE,
        library_id=settings.ZOTERO_LIBRARY_ID,
        api_key=settings.ZOTERO_API_KEY,
        timeout_seconds=settings.TOOL_TIMEOUT_SECONDS,
    )
    return ZoteroSearchOutput.model_validate(client.search_items(
        query=query,
        tag=tag,
        collection_key=collection_key,
        limit=limit,
        include_notes=include_notes,
    ))


if __name__ == "__main__":
    mcp.run(transport="stdio")
