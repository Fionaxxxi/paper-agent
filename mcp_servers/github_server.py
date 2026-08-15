"""通过 MCP stdio 暴露 GitHub 的固定只读端点。"""

from mcp.server import MCPServer

from core.config import settings
from tools.github_client import GitHubReadOnlyClient
from tools.mcp_github import GitHubInspectOutput, GitHubSearchOutput


mcp = MCPServer("paperagent-github", version="1.0.0", instructions="只读搜索和检查公开或已授权的 GitHub 仓库；不提供写操作。")


def _client() -> GitHubReadOnlyClient:
    return GitHubReadOnlyClient(base_url=settings.GITHUB_API_BASE_URL, token=settings.GITHUB_TOKEN, timeout_seconds=settings.TOOL_TIMEOUT_SECONDS)


@mcp.tool(annotations={"readOnlyHint": True}, structured_output=True)
def search_repositories(query: str, limit: int = settings.GITHUB_MAX_RESULTS) -> GitHubSearchOutput:
    """按研究主题、论文名或关键词搜索 GitHub 仓库。"""
    return GitHubSearchOutput.model_validate(_client().search_repositories(query=query, limit=limit))


@mcp.tool(annotations={"readOnlyHint": True}, structured_output=True)
def inspect_repository(repository: str, tree_limit: int = 100, activity_limit: int = 3) -> GitHubInspectOutput:
    """读取指定 owner/repo 的实现说明、结构、依赖与近期活动。"""
    return GitHubInspectOutput.model_validate(_client().inspect_repository(repository=repository, tree_limit=tree_limit, activity_limit=activity_limit))


if __name__ == "__main__":
    mcp.run(transport="stdio")
