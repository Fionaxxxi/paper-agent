"""经过验证的派生研究记忆：同调用元数据、写入门控与按需召回。"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field


MEMORY_TAG_RE = re.compile(r"<MEMORY_METADATA>\s*(\{.*?\})\s*</MEMORY_METADATA>", re.DOTALL)
TIME_SENSITIVE_SIGNALS = ("最新", "当前", "今年", "最近", "截至", "2025", "2026")
EXPLICIT_MEMORY_SIGNALS = ("基于之前", "继续上次", "上次结论", "之前总结", "还记得", "沿用之前")


class MemoryMetadata(BaseModel):
    worth_storing: bool = False
    memory_type: Literal["research_finding", "research_context", "user_research_topic", "none"] = "none"
    value_score: float = Field(default=0.0, ge=0.0, le=1.0)
    stability: Literal["stable", "evolving", "snapshot", "unknown"] = "unknown"
    time_sensitive: bool = False
    topic: str = ""


def memory_metadata_instruction(answer_hash_hint: str = "") -> str:
    return f"""
【内部长期记忆建议】在正常中文回答末尾追加且仅追加：
<MEMORY_METADATA>{{"worth_storing":true或false,"memory_type":"research_finding|research_context|user_research_topic|none","value_score":0到1,"stability":"stable|evolving|snapshot|unknown","time_sensitive":true或false,"topic":"简短研究主题"}}</MEMORY_METADATA>
该JSON仅是建议，不得改变正常回答。Smalltalk、一次性改写、简单公开事实和证据不足结论必须worth_storing=false。{answer_hash_hint}
"""


def parse_memory_metadata(text: str) -> tuple[str, dict[str, Any]]:
    match = MEMORY_TAG_RE.search(text)
    if not match:
        return text.strip(), {"status": "missing", **MemoryMetadata().model_dump()}
    clean = MEMORY_TAG_RE.sub("", text).strip()
    try:
        metadata = MemoryMetadata.model_validate(json.loads(match.group(1)))
        return clean, {"status": "valid", **metadata.model_dump()}
    except Exception as error:
        return clean, {"status": "invalid", "error_type": type(error).__name__, **MemoryMetadata().model_dump()}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _terms(text: str) -> set[str]:
    lowered = text.casefold()
    english = set(re.findall(r"[a-z][a-z0-9-]{2,}", lowered))
    chinese = {
        run[index:index + 2]
        for run in re.findall(r"[\u4e00-\u9fff]{2,}", lowered)
        for index in range(max(1, len(run) - 1))
    }
    return english | chinese


def _similarity(left: str, right: str) -> float:
    a, b = _terms(left), _terms(right)
    return len(a & b) / len(a | b) if a and b else 0.0


def _polarity_conflict(left: str, right: str) -> bool:
    markers = ("不支持", "无法", "没有", "并非", "未能", "not support", "cannot", "does not")
    return any(marker in left.casefold() for marker in markers) != any(
        marker in right.casefold() for marker in markers
    )


class LongTermMemoryStore:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript("""
            CREATE TABLE IF NOT EXISTS long_term_memories (
                memory_id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, topic TEXT NOT NULL,
                memory_type TEXT NOT NULL, content TEXT NOT NULL, content_hash TEXT NOT NULL,
                value_score REAL NOT NULL, stability TEXT NOT NULL, time_sensitive INTEGER NOT NULL,
                evidence_ids_json TEXT NOT NULL, source_trace_id TEXT NOT NULL,
                status TEXT NOT NULL, version INTEGER NOT NULL, created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL, valid_until TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_ltm_owner_topic ON long_term_memories(owner_id, topic, status);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_ltm_owner_hash ON long_term_memories(owner_id, content_hash);
            CREATE TABLE IF NOT EXISTS long_term_memory_conflicts (
                conflict_id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, topic TEXT NOT NULL,
                memory_type TEXT NOT NULL, existing_memory_id TEXT NOT NULL,
                candidate_content TEXT NOT NULL, candidate_hash TEXT NOT NULL,
                evidence_ids_json TEXT NOT NULL, source_trace_id TEXT NOT NULL,
                status TEXT NOT NULL, detected_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_ltm_conflict_owner ON long_term_memory_conflicts(owner_id, status, detected_at);
            """)

    def _connect(self):
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def write(self, *, owner_id: str, topic: str, memory_type: str, content: str,
              value_score: float, stability: str, time_sensitive: bool,
              evidence_ids: list[str], trace_id: str, snapshot_days: int = 30) -> dict[str, Any]:
        content_hash = hashlib.sha256(content.strip().encode("utf-8")).hexdigest()
        now = _now()
        with self._connect() as connection:
            exact = connection.execute(
                "SELECT * FROM long_term_memories WHERE owner_id=? AND content_hash=?",
                (owner_id, content_hash),
            ).fetchone()
            if exact:
                connection.execute("UPDATE long_term_memories SET updated_at=? WHERE memory_id=?", (now.isoformat(), exact["memory_id"]))
                return {"action": "merge", "reason": "exact_duplicate", "memory_id": exact["memory_id"], "version": exact["version"]}
            active = connection.execute(
                "SELECT * FROM long_term_memories WHERE owner_id=? AND topic=? AND memory_type=? AND status='active' ORDER BY version DESC",
                (owner_id, topic, memory_type),
            ).fetchall()
            related = next((row for row in active if _similarity(row["content"], content) >= 0.45), None)
            version = (max((row["version"] for row in active), default=0) + 1)
            action = "update" if related else "write"
            if related and _polarity_conflict(related["content"], content):
                conflict_id = "C-" + hashlib.sha256(
                    f"{owner_id}|{related['memory_id']}|{content_hash}".encode()
                ).hexdigest()[:16]
                connection.execute(
                    "INSERT OR IGNORE INTO long_term_memory_conflicts VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (conflict_id, owner_id, topic, memory_type, related["memory_id"], content,
                     content_hash, json.dumps(evidence_ids, ensure_ascii=False), trace_id,
                     "open", now.isoformat()),
                )
                return {
                    "action": "skip", "reason": "conflict_detected",
                    "memory_id": "", "conflict_memory_id": related["memory_id"],
                    "conflict_id": conflict_id, "version": related["version"],
                }
            if related:
                connection.execute("UPDATE long_term_memories SET status='superseded', updated_at=? WHERE memory_id=?", (now.isoformat(), related["memory_id"]))
            memory_id = "M-" + hashlib.sha256(f"{owner_id}|{topic}|{content_hash}".encode()).hexdigest()[:16]
            valid_until = (now + timedelta(days=snapshot_days)).isoformat() if time_sensitive else None
            connection.execute(
                "INSERT INTO long_term_memories VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (memory_id, owner_id, topic, memory_type, content, content_hash, value_score,
                 stability, int(time_sensitive), json.dumps(evidence_ids, ensure_ascii=False), trace_id,
                 "active", version, now.isoformat(), now.isoformat(), valid_until),
            )
        return {"action": action, "reason": "related_version" if related else "new_memory", "memory_id": memory_id, "version": version}

    def search(self, owner_id: str, query: str, limit: int = 3) -> list[dict[str, Any]]:
        now = _now().isoformat()
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM long_term_memories WHERE owner_id=? AND status='active' AND (valid_until IS NULL OR valid_until>?)",
                (owner_id, now),
            ).fetchall()
        ranked = []
        for row in rows:
            score = max(_similarity(query, row["topic"]), _similarity(query, row["content"]))
            if score > 0 or any(signal in query for signal in EXPLICIT_MEMORY_SIGNALS):
                item = dict(row)
                item["relevance_score"] = round(score, 4)
                item["evidence_ids"] = json.loads(item.pop("evidence_ids_json"))
                ranked.append(item)
        return sorted(ranked, key=lambda item: (item["relevance_score"], item["value_score"], item["updated_at"]), reverse=True)[:limit]

    def delete_owner(self, owner_id: str) -> int:
        with self._connect() as connection:
            connection.execute("DELETE FROM long_term_memory_conflicts WHERE owner_id=?", (owner_id,))
            cursor = connection.execute("DELETE FROM long_term_memories WHERE owner_id=?", (owner_id,))
            return cursor.rowcount

    def list_memories(self, owner_id: str, *, include_inactive: bool = False, limit: int = 50) -> list[dict[str, Any]]:
        where = "owner_id=?" if include_inactive else "owner_id=? AND status='active'"
        with self._connect() as connection:
            rows = connection.execute(
                f"SELECT * FROM long_term_memories WHERE {where} ORDER BY updated_at DESC LIMIT ?",
                (owner_id, max(1, min(limit, 200))),
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["evidence_ids"] = json.loads(item.pop("evidence_ids_json"))
            result.append(item)
        return result

    def list_conflicts(self, owner_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM long_term_memory_conflicts WHERE owner_id=? ORDER BY detected_at DESC LIMIT ?",
                (owner_id, max(1, min(limit, 200))),
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["evidence_ids"] = json.loads(item.pop("evidence_ids_json"))
            result.append(item)
        return result

    def delete_memory(self, owner_id: str, memory_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM long_term_memories WHERE owner_id=? AND memory_id=?",
                (owner_id, memory_id),
            )
            return cursor.rowcount > 0

    def expire_snapshots(self) -> int:
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE long_term_memories SET status='expired', updated_at=? "
                "WHERE status='active' AND valid_until IS NOT NULL AND valid_until<=?",
                (_now().isoformat(), _now().isoformat()),
            )
            return cursor.rowcount

    def statistics(self, owner_id: str) -> dict[str, int]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT status, COUNT(*) AS count FROM long_term_memories WHERE owner_id=? GROUP BY status",
                (owner_id,),
            ).fetchall()
            conflicts = connection.execute(
                "SELECT COUNT(*) AS count FROM long_term_memory_conflicts WHERE owner_id=? AND status='open'",
                (owner_id,),
            ).fetchone()["count"]
        counts = {row["status"]: row["count"] for row in rows}
        return {
            "active": counts.get("active", 0), "superseded": counts.get("superseded", 0),
            "expired": counts.get("expired", 0), "open_conflicts": conflicts,
            "total": sum(counts.values()),
        }


def memory_need_detection(state: dict[str, Any]) -> dict[str, Any]:
    query = str(state.get("query") or "")
    explicit = any(signal in query for signal in EXPLICIT_MEMORY_SIGNALS)
    l3 = state.get("task_level") == "L3"
    return {"needed": explicit or l3, "reason": "explicit_history" if explicit else "l3_reuse" if l3 else "not_needed"}


def evaluate_memory_write(state: dict[str, Any], threshold: float = 0.75) -> dict[str, Any]:
    metadata = state.get("memory_metadata", {})
    if metadata.get("status") != "valid" or not metadata.get("worth_storing"):
        return {"allowed": False, "reason": "metadata_not_recommended"}
    answer_hash = hashlib.sha256(str(state.get("answer", "")).strip().encode("utf-8")).hexdigest()
    if metadata.get("source_answer_hash") and metadata.get("source_answer_hash") != answer_hash:
        return {"allowed": False, "reason": "answer_changed_after_metadata"}
    if not state.get("answer_verification", {}).get("passed"):
        return {"allowed": False, "reason": "answer_not_verified"}
    if state.get("citation_validation", {}).get("enabled") and not state.get("citation_validation", {}).get("passed"):
        return {"allowed": False, "reason": "citation_not_verified"}
    if state.get("claim_evidence_validation", {}).get("enabled") and not state.get("claim_evidence_validation", {}).get("passed"):
        return {"allowed": False, "reason": "claim_not_verified"}
    if not state.get("evidence_store", {}).get("evidence") and not state.get("documents"):
        return {"allowed": False, "reason": "no_traceable_evidence"}
    if float(metadata.get("value_score", 0)) < threshold:
        return {"allowed": False, "reason": "value_below_threshold"}
    if metadata.get("stability") == "unknown":
        return {"allowed": False, "reason": "stability_unknown"}
    return {"allowed": True, "reason": "policy_passed"}
