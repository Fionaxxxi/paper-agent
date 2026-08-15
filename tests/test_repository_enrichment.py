from tools.contracts import ToolResult

from nodes import repository_enrich as enrich_module
from nodes.evidence_store import evidence_store_node


def _state(query: str):
    return {
        "query": query,
        "task_level": "L3",
        "documents": [{"title": "GraphRAG", "source": "arxiv", "entry_id": "paper-1", "content": "graph rag paper"}],
        "tools_used": ["paper.search.arxiv"],
        "paper_metadata": {"tool_executions": []},
        "research_analysis": {"topic": "GraphRAG"},
    }


def test_generic_code_intent_suggests_github_without_external_call(monkeypatch):
    monkeypatch.setattr(enrich_module.settings, "GITHUB_ENRICHMENT_ENABLED", True)
    monkeypatch.setattr(enrich_module.paper_tool_executor, "execute", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("不应调用外部工具")))

    result = enrich_module.repository_enrich_node(_state("分析这篇论文的代码实现和复现难度"))

    assert result["repository_enrichment"]["status"] == "suggested"
    assert "repository_evidence" not in result


def test_explicit_github_intent_stays_disabled_without_operator_opt_in(monkeypatch):
    monkeypatch.setattr(enrich_module.settings, "GITHUB_ENRICHMENT_ENABLED", False)
    monkeypatch.setattr(enrich_module.paper_tool_executor, "execute", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("不应调用外部工具")))

    result = enrich_module.repository_enrich_node(_state("用 GitHub 仓库分析论文实现"))

    assert result["repository_enrichment"]["status"] == "disabled"
    assert result["repository_enrichment"]["reason"] == "github_enrichment_config_disabled"


def test_double_opt_in_collects_repository_as_typed_evidence(monkeypatch):
    monkeypatch.setattr(enrich_module.settings, "GITHUB_ENRICHMENT_ENABLED", True)
    results = iter([
        ToolResult(success=True, tool_name="code.repository.search.github.mcp", tool_version="1.0.0", source="github_mcp", data={"repositories": [{"full_name": "microsoft/graphrag"}], "total_matches": 1}, metadata={"tool_origin": "mcp"}),
        ToolResult(success=True, tool_name="code.repository.inspect.github.mcp", tool_version="1.0.0", source="github_mcp", data={
            "repository": {"full_name": "microsoft/graphrag", "description": "GraphRAG implementation", "url": "https://github.com/microsoft/graphrag", "stars": 100, "language": "Python", "default_branch": "main"},
            "readme": "GraphRAG code and indexing", "tree_paths": ["pyproject.toml"],
            "dependencies": [{"path": "pyproject.toml", "content": ""}], "open_issues": [],
            "releases": [{"tag": "v1", "name": "", "url": "", "published_at": ""}],
            "recent_commits": [{"sha": "abc", "message": "update indexing", "url": "", "date": ""}],
        }, metadata={"tool_origin": "mcp"}),
    ])
    monkeypatch.setattr(enrich_module.paper_tool_executor, "execute", lambda *args, **kwargs: next(results))

    enriched = enrich_module.repository_enrich_node(_state("请结合 GitHub 仓库分析 GraphRAG 的代码实现"))

    assert enriched["repository_enrichment"]["status"] == "collected"
    assert enriched["repository_enrichment"]["selected_repository"] == "microsoft/graphrag"
    assert len(enriched["paper_metadata"]["tool_executions"]) == 2
    assert enriched["repository_evidence"][0]["evidence_type"] == "repository"

    stored = evidence_store_node({
        **_state("请结合 GitHub 仓库分析 GraphRAG 的代码实现"),
        **enriched,
        "research_schedule": {"enabled": True, "waves": [
            {"tasks": [{"task_id": "T1", "task_kind": "retrieval", "query": "GraphRAG implementation", "objective": "检查实现", "depends_on": []}]},
            {"tasks": [{"task_id": "T2", "task_kind": "synthesis", "query": "", "objective": "论文代码对照", "depends_on": ["T1"]}]},
        ]},
    })
    repository_record = next(item for item in stored["evidence_store"]["evidence"] if item["source"] == "github")
    assert repository_record["evidence_type"] == "repository"
    assert repository_record["locator"] == "https://github.com/microsoft/graphrag"
