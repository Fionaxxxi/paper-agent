"""GitHub 只读 MCP 工具的 PaperAgent 注册定义。"""

from __future__ import annotations

import sys
from pathlib import Path

from pydantic import BaseModel, Field, field_validator

from tools.contracts import RetryPolicy, ToolRiskLevel, ToolSpec
from tools.mcp_adapter import MCPServerIdentity, MCPToolAdapter
from tools.mcp_stdio_client import StdioMCPClient


class GitHubRepository(BaseModel):
    full_name: str = ""
    owner: str = ""
    name: str = ""
    description: str = ""
    url: str = ""
    stars: int = 0
    language: str = ""
    topics: list[str] = Field(default_factory=list)
    default_branch: str = ""
    updated_at: str = ""


class GitHubSearchInput(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    limit: int = Field(default=5, ge=1, le=10)


class GitHubSearchOutput(BaseModel):
    repositories: list[GitHubRepository] = Field(default_factory=list)
    total_matches: int = Field(ge=0)


class GitHubInspectInput(BaseModel):
    repository: str = Field(pattern=r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
    tree_limit: int = Field(default=100, ge=1, le=300)
    activity_limit: int = Field(default=3, ge=1, le=5)

    @field_validator("repository")
    @classmethod
    def reject_relative_path_parts(cls, value: str) -> str:
        if any(part in {".", ".."} for part in value.split("/")):
            raise ValueError("repository 不能包含相对路径片段")
        return value


class DependencyFile(BaseModel):
    path: str
    content: str = ""


class IssueSummary(BaseModel):
    number: int | None = None
    title: str = ""
    url: str = ""
    updated_at: str = ""


class ReleaseSummary(BaseModel):
    tag: str = ""
    name: str = ""
    url: str = ""
    published_at: str = ""


class CommitSummary(BaseModel):
    sha: str = ""
    message: str = ""
    url: str = ""
    date: str = ""


class GitHubInspectOutput(BaseModel):
    repository: GitHubRepository
    readme: str = ""
    tree_paths: list[str] = Field(default_factory=list)
    dependencies: list[DependencyFile] = Field(default_factory=list)
    open_issues: list[IssueSummary] = Field(default_factory=list)
    releases: list[ReleaseSummary] = Field(default_factory=list)
    recent_commits: list[CommitSummary] = Field(default_factory=list)


def _client() -> StdioMCPClient:
    root = Path(__file__).resolve().parents[1]
    return StdioMCPClient(command=sys.executable, args=("-m", "mcp_servers.github_server"), cwd=str(root))


def build_github_search_mcp_tool() -> MCPToolAdapter:
    return MCPToolAdapter(
        client=_client(), remote_tool_name="search_repositories",
        spec=ToolSpec(name="code.repository.search.github.mcp", version="1.0.0", description="通过只读 GitHub MCP 搜索与论文或研究主题相关的代码仓库。", input_model=GitHubSearchInput, output_model=GitHubSearchOutput, provider="github_mcp", capabilities=("repository.search",), risk_level=ToolRiskLevel.READ_ONLY, timeout_seconds=45, retry_policy=RetryPolicy(max_attempts=1), cache_policy="none"),
        server=MCPServerIdentity("paperagent-github", "1.0.0", "stdio"),
    )


def build_github_inspect_mcp_tool() -> MCPToolAdapter:
    return MCPToolAdapter(
        client=_client(), remote_tool_name="inspect_repository",
        spec=ToolSpec(name="code.repository.inspect.github.mcp", version="1.0.0", description="只读检查 GitHub 仓库的 README、目录、依赖和近期活动。", input_model=GitHubInspectInput, output_model=GitHubInspectOutput, provider="github_mcp", capabilities=("repository.inspect",), risk_level=ToolRiskLevel.READ_ONLY, timeout_seconds=60, retry_policy=RetryPolicy(max_attempts=1), cache_policy="none"),
        server=MCPServerIdentity("paperagent-github", "1.0.0", "stdio"),
    )
