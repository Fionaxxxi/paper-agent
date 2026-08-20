import hashlib
import sqlite3

from memory.long_term_memory import (
    LongTermMemoryStore,
    evaluate_memory_write,
    parse_memory_metadata,
)
import nodes.memory_retrieve as retrieve_module
from context.context_builder import build_skill_context


def _verified_state(answer: str = "该方法支持可验证的研究结论。") -> dict:
    return {
        "answer": answer,
        "memory_metadata": {
            "status": "valid",
            "worth_storing": True,
            "memory_type": "research_finding",
            "value_score": 0.9,
            "stability": "stable",
            "time_sensitive": False,
            "topic": "Agent Memory",
            "source_answer_hash": hashlib.sha256(answer.encode("utf-8")).hexdigest(),
        },
        "answer_verification": {"passed": True},
        "citation_validation": {"enabled": True, "passed": True},
        "claim_evidence_validation": {"enabled": True, "passed": True},
        "evidence_store": {"evidence": [{"evidence_id": "EV-1"}]},
    }


def test_memory_metadata_is_parsed_and_removed_from_user_answer():
    raw = '研究结论正文。\n<MEMORY_METADATA>{"worth_storing":true,"memory_type":"research_finding","value_score":0.88,"stability":"stable","time_sensitive":false,"topic":"Agent Memory"}</MEMORY_METADATA>'
    answer, metadata = parse_memory_metadata(raw)
    assert answer == "研究结论正文。"
    assert metadata["status"] == "valid"
    assert metadata["value_score"] == 0.88


def test_invalid_memory_metadata_keeps_readable_answer_and_is_rejected():
    answer, metadata = parse_memory_metadata(
        "仍可阅读的答案。<MEMORY_METADATA>{broken}</MEMORY_METADATA>"
    )
    assert answer == "仍可阅读的答案。"
    assert metadata["status"] == "invalid"
    state = _verified_state(answer)
    state["memory_metadata"] = metadata
    assert evaluate_memory_write(state)["reason"] == "metadata_not_recommended"


def test_write_gate_requires_final_verified_unchanged_answer():
    state = _verified_state()
    assert evaluate_memory_write(state)["allowed"] is True
    state["answer_verification"] = {"passed": False}
    assert evaluate_memory_write(state)["reason"] == "answer_not_verified"
    state = _verified_state()
    state["answer"] = "反思后被修改的答案"
    assert evaluate_memory_write(state)["reason"] == "answer_changed_after_metadata"


def test_memory_store_writes_merges_and_versions_related_finding(tmp_path):
    store = LongTermMemoryStore(tmp_path / "memory.db")
    common = dict(owner_id="u1", topic="Agent Memory", memory_type="research_finding",
                  value_score=0.9, stability="stable", time_sensitive=False,
                  evidence_ids=["EV-1"], trace_id="T-1")
    first = store.write(content="Agent Memory 支持长期任务上下文复用。", **common)
    duplicate = store.write(content="Agent Memory 支持长期任务上下文复用。", **common)
    updated = store.write(content="Agent Memory 支持长期任务上下文复用与跨会话研究。", **common)
    assert first["action"] == "write"
    assert duplicate["action"] == "merge"
    assert updated["action"] == "update"
    assert updated["version"] == 2


def test_memory_store_skips_related_polarity_conflict(tmp_path):
    store = LongTermMemoryStore(tmp_path / "memory.db")
    common = dict(owner_id="u1", topic="GraphRAG", memory_type="research_finding",
                  value_score=0.9, stability="stable", time_sensitive=False,
                  evidence_ids=["EV-1"], trace_id="T-1")
    original = store.write(content="GraphRAG 支持全局关系研究。", **common)
    conflict = store.write(content="GraphRAG 不支持全局关系研究。", **common)
    assert original["action"] == "write"
    assert conflict["action"] == "skip"
    assert conflict["reason"] == "conflict_detected"
    assert conflict["conflict_memory_id"] == original["memory_id"]


def test_memory_retrieval_is_owner_isolated_and_injected_on_demand(tmp_path, monkeypatch):
    db_path = tmp_path / "memory.db"
    store = LongTermMemoryStore(db_path)
    common = dict(topic="Agent Memory", memory_type="research_finding", value_score=0.9,
                  stability="stable", time_sensitive=False, evidence_ids=["EV-1"], trace_id="T-1")
    store.write(owner_id="conversation-a", content="Agent Memory 支持跨会话研究上下文。", **common)
    store.write(owner_id="conversation-b", content="另一个用户的私有研究结论。", **common)
    monkeypatch.setattr(retrieve_module.settings, "LONG_TERM_MEMORY_DB_PATH", str(db_path))

    result = retrieve_module.memory_retrieve_node({
        "conversation_id": "conversation-a",
        "query": "基于之前的 Agent Memory 结论继续分析",
        "task_level": "L2",
        "history_text": "最近对话",
        "paper_metadata": {},
    })
    context = build_skill_context({
        "task_type": "qa", "history_text": "最近对话",
        "long_term_memory_context": result["long_term_memory_context"],
    })
    assert result["memory_retrieval"]["status"] == "retrieved"
    assert result["memory_retrieval"]["additional_llm_calls"] == 0
    assert "跨会话研究上下文" in context["history_text"]
    assert "另一个用户" not in context["history_text"]


def test_independent_l1_query_does_not_load_memory(tmp_path, monkeypatch):
    monkeypatch.setattr(retrieve_module.settings, "LONG_TERM_MEMORY_DB_PATH", str(tmp_path / "memory.db"))
    result = retrieve_module.memory_retrieve_node({
        "conversation_id": "conversation-a", "query": "什么是RAG？",
        "task_level": "L1", "paper_metadata": {},
    })
    assert result["memory_retrieval"]["status"] == "not_needed"
    assert result["retrieved_memories"] == []


def test_expired_snapshot_is_not_retrieved(tmp_path):
    db_path = tmp_path / "memory.db"
    store = LongTermMemoryStore(db_path)
    written = store.write(
        owner_id="u1", topic="最新 Agent Memory", memory_type="research_finding",
        content="当前最新结论。", value_score=0.9, stability="snapshot",
        time_sensitive=True, evidence_ids=["EV-1"], trace_id="T-1", snapshot_days=1,
    )
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "UPDATE long_term_memories SET valid_until='2000-01-01T00:00:00+00:00' WHERE memory_id=?",
            (written["memory_id"],),
        )
    assert store.search("u1", "基于之前的最新 Agent Memory 结论") == []


def test_conflict_is_persisted_for_owner_audit(tmp_path):
    store = LongTermMemoryStore(tmp_path / "memory.db")
    common = dict(owner_id="u1", topic="GraphRAG", memory_type="research_finding",
                  value_score=0.9, stability="stable", time_sensitive=False,
                  evidence_ids=["EV-1"], trace_id="T-1")
    store.write(content="GraphRAG 支持全局关系研究。", **common)
    conflict = store.write(content="GraphRAG 不支持全局关系研究。", **common)
    audits = store.list_conflicts("u1")
    assert audits[0]["conflict_id"] == conflict["conflict_id"]
    assert audits[0]["status"] == "open"
    assert store.statistics("u1")["open_conflicts"] == 1


def test_snapshot_cleanup_marks_expired_and_preserves_audit_record(tmp_path):
    db_path = tmp_path / "memory.db"
    store = LongTermMemoryStore(db_path)
    written = store.write(
        owner_id="u1", topic="最新论文", memory_type="research_finding", content="2026快照",
        value_score=0.9, stability="snapshot", time_sensitive=True,
        evidence_ids=["EV-1"], trace_id="T-1", snapshot_days=1,
    )
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            "UPDATE long_term_memories SET valid_until='2000-01-01T00:00:00+00:00' WHERE memory_id=?",
            (written["memory_id"],),
        )
    assert store.expire_snapshots() == 1
    records = store.list_memories("u1", include_inactive=True)
    assert records[0]["status"] == "expired"
    assert store.statistics("u1")["expired"] == 1


def test_memory_delete_is_scoped_to_owner_and_owner_delete_clears_conflicts(tmp_path):
    store = LongTermMemoryStore(tmp_path / "memory.db")
    common = dict(topic="RAG", memory_type="research_finding", value_score=0.9,
                  stability="stable", time_sensitive=False, evidence_ids=[], trace_id="T")
    first = store.write(owner_id="u1", content="RAG 支持检索增强。", **common)
    store.write(owner_id="u2", content="另一个 Owner 的记忆。", **common)
    store.write(owner_id="u1", content="RAG 不支持检索增强。", **common)
    assert store.delete_memory("u2", first["memory_id"]) is False
    assert store.delete_memory("u1", first["memory_id"]) is True
    assert len(store.list_memories("u2")) == 1
    store.delete_owner("u1")
    assert store.list_memories("u1", include_inactive=True) == []
    assert store.list_conflicts("u1") == []
