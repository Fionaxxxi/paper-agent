import json

import pytest

import memory.conversation_memory as conversation_memory
import services.paper_agent_service as service_module
from memory.structured_memory import MemoryContext, SQLiteMemoryStore, build_context_text


def test_sqlite_memory_persists_messages_and_returns_recent_window(tmp_path):
    store = SQLiteMemoryStore(tmp_path / "memory.db")
    for index in range(8):
        store.append_message("c1", "user", f"message-{index}")

    context = SQLiteMemoryStore(tmp_path / "memory.db").load_context(
        "c1", recent_limit=3, summary_max_chars=200
    )

    assert [item["content"] for item in context.recent_messages] == [
        "message-5",
        "message-6",
        "message-7",
    ]
    assert context.total_message_count == 8
    assert context.compressed_message_count == 5
    assert "5 条" in context.older_summary


def test_research_context_is_structured_deduplicated_and_conversation_scoped(tmp_path):
    store = SQLiteMemoryStore(tmp_path / "memory.db")
    store.update_research_context(
        "c1",
        preferences=["中文回答"],
        topics=["Agent Memory"],
        papers=["ReAct", "ReAct"],
    )
    store.update_research_context("c1", topics=["Agent Loop"], papers=["Reflexion"])

    first = store.load_context("c1")
    second = store.load_context("c2")

    assert first.user_preferences == ["中文回答"]
    assert first.active_topics == ["Agent Loop", "Agent Memory"]
    assert first.active_papers == ["Reflexion", "ReAct"]
    assert second.active_topics == []


def test_context_compression_respects_budget_and_keeps_each_memory_layer():
    context = MemoryContext(
        conversation_id="c1",
        recent_messages=[{"role": "user", "content": "最近的问题" * 20}],
        older_summary="旧摘要" * 40,
        user_preferences=["中文回答"],
        active_topics=["Research Agent"],
        active_papers=["ReAct"],
    )

    text = build_context_text(context, max_chars=240)

    assert len(text) <= 240
    assert "用户偏好" in text
    assert "旧摘要" in text
    assert "最近的问题" in text


def test_checkpoint_round_trip_and_conversation_delete(tmp_path):
    store = SQLiteMemoryStore(tmp_path / "memory.db")
    store.append_message("c1", "user", "研究 Agent 架构")
    store.save_checkpoint("c1", "research-plan", {"status": "planned", "tasks": ["T1"]})

    assert store.load_checkpoint("c1", "research-plan") == {
        "status": "planned",
        "tasks": ["T1"],
    }

    store.delete_conversation("c1")

    assert store.get_messages("c1") == []
    assert store.load_checkpoint("c1", "research-plan") is None


def test_invalid_message_role_is_rejected(tmp_path):
    store = SQLiteMemoryStore(tmp_path / "memory.db")

    with pytest.raises(ValueError, match="role"):
        store.append_message("c1", "tool", "unsafe")


def test_legacy_json_is_migrated_once_into_sqlite(tmp_path, monkeypatch):
    legacy_dir = tmp_path / "legacy"
    legacy_dir.mkdir()
    (legacy_dir / "old.json").write_text(
        json.dumps(
            {
                "messages": [
                    {"role": "user", "content": "旧问题"},
                    {"role": "assistant", "content": "旧回答"},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(conversation_memory, "LEGACY_MEMORY_DIR", legacy_dir)
    monkeypatch.setattr(
        conversation_memory.settings, "MEMORY_DB_PATH", str(tmp_path / "memory.db")
    )
    monkeypatch.setattr(conversation_memory, "_default_store", None)

    first = conversation_memory.load_history("old")
    second = conversation_memory.load_history("old")

    assert [item["content"] for item in first] == ["旧问题", "旧回答"]
    assert len(second) == 2


def test_service_injects_compressed_context_and_updates_research_memory(monkeypatch):
    context = MemoryContext(
        conversation_id="c1",
        recent_messages=[{"role": "user", "content": "继续比较"}],
        older_summary="更早对话摘要：讨论了 ReAct",
        active_topics=["Agent 架构"],
        active_papers=["ReAct"],
        total_message_count=9,
        compressed_message_count=8,
    )
    captured = {}

    class FakeGraph:
        def invoke(self, state):
            captured["state"] = state
            return {
                "answer": "基于 ReAct 的研究回答",
                "documents": [{"title": "ReAct"}],
                "paper_metadata": {},
            }

    monkeypatch.setattr(service_module, "build_graph", lambda: FakeGraph())
    monkeypatch.setattr(service_module, "load_memory_context", lambda _: context)
    monkeypatch.setattr(service_module, "save_message", lambda *args: None)
    monkeypatch.setattr(
        service_module,
        "update_research_memory",
        lambda conversation_id, **kwargs: captured.update(
            {"memory_update": (conversation_id, kwargs)}
        ),
    )

    result = service_module.PaperAgentService().chat("比较 Agent 架构", "c1")

    assert "当前研究主题：Agent 架构" in captured["state"]["history_text"]
    assert "最近对话" in captured["state"]["history_text"]
    assert captured["memory_update"][0] == "c1"
    assert captured["memory_update"][1]["documents"][0]["title"] == "ReAct"
    assert result["paper_metadata"]["memory_compressed_message_count"] == 8
