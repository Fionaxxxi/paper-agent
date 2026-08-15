"""在双重显式授权下补充 GitHub 实现证据。"""

from __future__ import annotations

import re
from typing import Any

from agent.state import AgentState
from core.config import settings
from tools.runtime import paper_tool_executor, paper_tool_router


_GITHUB_INTENT = re.compile(r"github(?:\s*仓库)?|github\s+repository", re.IGNORECASE)
_CODE_INTENT = re.compile(r"repository|\brepo\b|implementation|reproduc|source\s+code|代码|仓库|实现|复现|开源", re.IGNORECASE)


def repository_enrichment_decision(state: AgentState) -> dict[str, Any]:
    """区分关闭、建议和真正授权，避免静默发送用户内容。"""
    query = " ".join(str(state.get(key) or "") for key in ("query", "resolved_query", "original_query"))
    if state.get("task_level") != "L3" or not _CODE_INTENT.search(query):
        return {"enabled": False, "status": "not_applicable", "reason": "no_explicit_repository_intent"}
    if not _GITHUB_INTENT.search(query):
        return {"enabled": False, "status": "suggested", "reason": "github_not_explicitly_requested"}
    if not settings.GITHUB_ENRICHMENT_ENABLED:
        return {"enabled": False, "status": "disabled", "reason": "github_enrichment_config_disabled"}
    return {"enabled": True, "status": "authorized", "reason": "config_and_query_authorized"}


def _execution(tool_result: Any, capability: str, tool_name: str) -> dict[str, Any]:
    return {
        "tool_name": tool_result.tool_name,
        "tool_version": tool_result.tool_version,
        "tool_success": tool_result.success,
        "tool_error_code": tool_result.error_code,
        "tool_error_message": tool_result.error_message,
        "tool_latency_seconds": tool_result.latency_seconds,
        "tool_attempt_count": tool_result.attempt_count,
        "tool_source": tool_result.source,
        "tool_metadata": dict(tool_result.metadata),
        "tool_route": {"capability": capability, "source": "github", "tool_name": tool_name},
    }


def _search_query(state: AgentState) -> str:
    documents = state.get("documents", [])
    if documents and documents[0].get("title"):
        return f'"{str(documents[0]["title"])[:300]}"'
    return str(state.get("research_analysis", {}).get("topic") or "")[:300]


def _repository_document(payload: dict[str, Any]) -> dict[str, Any]:
    repository = payload.get("repository", {})
    dependency_paths = [item.get("path", "") for item in payload.get("dependencies", [])]
    release_tags = [item.get("tag", "") for item in payload.get("releases", [])]
    commit_messages = [item.get("message", "") for item in payload.get("recent_commits", [])]
    content = "\n".join(filter(None, [
        repository.get("description", ""), payload.get("readme", "")[:6000],
        f"依赖文件：{', '.join(dependency_paths)}" if dependency_paths else "",
        f"近期版本：{', '.join(release_tags)}" if release_tags else "",
        f"近期提交：{'；'.join(commit_messages)}" if commit_messages else "",
    ]))
    return {
        "title": f"代码仓库：{repository.get('full_name', 'unknown')}",
        "source": "github", "evidence_type": "repository",
        "entry_id": repository.get("full_name", ""), "url": repository.get("url", ""),
        "content": content, "year": None, "retrieval_score": 1.0,
        "repository_metadata": {
            "stars": repository.get("stars", 0), "language": repository.get("language", ""),
            "default_branch": repository.get("default_branch", ""),
            "tree_file_count": len(payload.get("tree_paths", [])),
            "dependency_files": dependency_paths,
            "open_issue_count": len(payload.get("open_issues", [])),
            "release_count": len(payload.get("releases", [])),
            "recent_commit_count": len(payload.get("recent_commits", [])),
        },
    }


def repository_enrich_node(state: AgentState) -> AgentState:
    decision = repository_enrichment_decision(state)
    if not decision["enabled"]:
        return {"repository_enrichment": decision}

    executions = list(state.get("paper_metadata", {}).get("tool_executions", []))
    tools_used = list(state.get("tools_used", []))
    try:
        search_tool = paper_tool_router.resolve("repository.search", "github")
        search = paper_tool_executor.execute(search_tool, {"query": _search_query(state), "limit": 3})
    except KeyError as error:
        return {"repository_enrichment": {**decision, "status": "failed", "error": str(error)}}
    executions.append(_execution(search, "repository.search", search_tool))
    if search_tool not in tools_used:
        tools_used.append(search_tool)
    candidates = (search.data or {}).get("repositories", []) if search.success and isinstance(search.data, dict) else []
    if not candidates:
        return {
            "repository_evidence": [], "tools_used": tools_used,
            "repository_enrichment": {**decision, "status": "empty" if search.success else "failed", "candidate_count": 0, "error": search.error_message},
            "paper_metadata": {**state.get("paper_metadata", {}), "tool_executions": executions},
        }

    try:
        inspect_tool = paper_tool_router.resolve("repository.inspect", "github")
        inspected = paper_tool_executor.execute(inspect_tool, {"repository": candidates[0]["full_name"], "tree_limit": 100, "activity_limit": 3})
    except KeyError as error:
        return {
            "repository_evidence": [], "tools_used": tools_used,
            "repository_enrichment": {**decision, "status": "failed", "candidate_count": len(candidates), "error": str(error)},
            "paper_metadata": {**state.get("paper_metadata", {}), "tool_executions": executions},
        }
    executions.append(_execution(inspected, "repository.inspect", inspect_tool))
    if inspect_tool not in tools_used:
        tools_used.append(inspect_tool)
    evidence = [_repository_document(inspected.data)] if inspected.success and isinstance(inspected.data, dict) else []
    return {
        "repository_evidence": evidence, "tools_used": tools_used,
        "repository_enrichment": {**decision, "status": "collected" if evidence else "failed", "candidate_count": len(candidates), "selected_repository": candidates[0].get("full_name", ""), "error": inspected.error_message},
        "paper_metadata": {**state.get("paper_metadata", {}), "tool_executions": executions},
    }
