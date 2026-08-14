"""面向 Research Agent 的 SQLite 结构化记忆与检查点存储。"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _unique_text(values: list[str], limit: int) -> list[str]:
    result: list[str] = []
    for value in values:
        normalized = str(value or "").strip()
        if normalized and normalized not in result:
            result.append(normalized)
        if len(result) >= limit:
            break
    return result


@dataclass
class MemoryContext:
    conversation_id: str
    recent_messages: list[dict[str, Any]] = field(default_factory=list)
    older_summary: str = ""
    user_preferences: list[str] = field(default_factory=list)
    active_topics: list[str] = field(default_factory=list)
    active_papers: list[str] = field(default_factory=list)
    total_message_count: int = 0
    compressed_message_count: int = 0


class SQLiteMemoryStore:
    """每次操作使用独立连接，避免在 Web 请求之间共享游标。"""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    conversation_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(conversation_id) REFERENCES conversations(conversation_id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_messages_conversation_id
                    ON messages(conversation_id, id);
                CREATE TABLE IF NOT EXISTS research_context (
                    conversation_id TEXT PRIMARY KEY,
                    user_preferences_json TEXT NOT NULL DEFAULT '[]',
                    active_topics_json TEXT NOT NULL DEFAULT '[]',
                    active_papers_json TEXT NOT NULL DEFAULT '[]',
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(conversation_id) REFERENCES conversations(conversation_id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS checkpoints (
                    conversation_id TEXT NOT NULL,
                    checkpoint_key TEXT NOT NULL,
                    state_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY(conversation_id, checkpoint_key),
                    FOREIGN KEY(conversation_id) REFERENCES conversations(conversation_id) ON DELETE CASCADE
                );
                """
            )

    def _ensure_conversation(self, connection: sqlite3.Connection, conversation_id: str) -> None:
        now = _utc_now()
        connection.execute(
            """
            INSERT INTO conversations(conversation_id, created_at, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(conversation_id) DO UPDATE SET updated_at=excluded.updated_at
            """,
            (conversation_id, now, now),
        )

    def append_message(self, conversation_id: str, role: str, content: str) -> None:
        if role not in {"user", "assistant", "system"}:
            raise ValueError("role must be user, assistant or system")
        with self._connect() as connection:
            self._ensure_conversation(connection, conversation_id)
            connection.execute(
                "INSERT INTO messages(conversation_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                (conversation_id, role, str(content), _utc_now()),
            )

    def get_messages(self, conversation_id: str, limit: int | None = None) -> list[dict[str, Any]]:
        with self._connect() as connection:
            if limit is None:
                rows = connection.execute(
                    "SELECT role, content, created_at FROM messages WHERE conversation_id=? ORDER BY id",
                    (conversation_id,),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT role, content, created_at FROM (
                        SELECT id, role, content, created_at FROM messages
                        WHERE conversation_id=? ORDER BY id DESC LIMIT ?
                    ) ORDER BY id
                    """,
                    (conversation_id, max(0, limit)),
                ).fetchall()
        return [dict(row) for row in rows]

    def update_research_context(
        self,
        conversation_id: str,
        *,
        preferences: list[str] | None = None,
        topics: list[str] | None = None,
        papers: list[str] | None = None,
    ) -> None:
        current = self._load_research_context(conversation_id)
        merged_preferences = _unique_text([*(preferences or []), *current["user_preferences"]], 10)
        merged_topics = _unique_text([*(topics or []), *current["active_topics"]], 8)
        merged_papers = _unique_text([*(papers or []), *current["active_papers"]], 12)
        with self._connect() as connection:
            self._ensure_conversation(connection, conversation_id)
            connection.execute(
                """
                INSERT INTO research_context(
                    conversation_id, user_preferences_json, active_topics_json,
                    active_papers_json, updated_at
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(conversation_id) DO UPDATE SET
                    user_preferences_json=excluded.user_preferences_json,
                    active_topics_json=excluded.active_topics_json,
                    active_papers_json=excluded.active_papers_json,
                    updated_at=excluded.updated_at
                """,
                (
                    conversation_id,
                    json.dumps(merged_preferences, ensure_ascii=False),
                    json.dumps(merged_topics, ensure_ascii=False),
                    json.dumps(merged_papers, ensure_ascii=False),
                    _utc_now(),
                ),
            )

    def _load_research_context(self, conversation_id: str) -> dict[str, list[str]]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM research_context WHERE conversation_id=?",
                (conversation_id,),
            ).fetchone()
        if row is None:
            return {"user_preferences": [], "active_topics": [], "active_papers": []}
        return {
            "user_preferences": json.loads(row["user_preferences_json"]),
            "active_topics": json.loads(row["active_topics_json"]),
            "active_papers": json.loads(row["active_papers_json"]),
        }

    @staticmethod
    def summarize_messages(messages: list[dict[str, Any]], max_chars: int) -> str:
        if not messages or max_chars <= 0:
            return ""
        lines = [f"{('用户' if item['role'] == 'user' else '助手')}：{item['content']}" for item in messages]
        header = f"更早对话摘要（{len(messages)} 条，提取式压缩）：\n"
        available = max(0, max_chars - len(header))
        joined = "\n".join(lines)
        if len(joined) > available:
            joined = joined[-available:]
        return header + joined

    def load_context(
        self,
        conversation_id: str,
        *,
        recent_limit: int = 6,
        summary_max_chars: int = 1200,
    ) -> MemoryContext:
        messages = self.get_messages(conversation_id)
        recent = messages[-recent_limit:] if recent_limit > 0 else []
        older = messages[:-recent_limit] if recent_limit > 0 else messages
        research = self._load_research_context(conversation_id)
        return MemoryContext(
            conversation_id=conversation_id,
            recent_messages=recent,
            older_summary=self.summarize_messages(older, summary_max_chars),
            total_message_count=len(messages),
            compressed_message_count=len(older),
            **research,
        )

    def save_checkpoint(self, conversation_id: str, checkpoint_key: str, state: dict[str, Any]) -> None:
        with self._connect() as connection:
            self._ensure_conversation(connection, conversation_id)
            connection.execute(
                """
                INSERT INTO checkpoints(conversation_id, checkpoint_key, state_json, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(conversation_id, checkpoint_key) DO UPDATE SET
                    state_json=excluded.state_json, created_at=excluded.created_at
                """,
                (conversation_id, checkpoint_key, json.dumps(state, ensure_ascii=False, default=str), _utc_now()),
            )

    def load_checkpoint(self, conversation_id: str, checkpoint_key: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT state_json FROM checkpoints WHERE conversation_id=? AND checkpoint_key=?",
                (conversation_id, checkpoint_key),
            ).fetchone()
        return json.loads(row["state_json"]) if row else None

    def delete_conversation(self, conversation_id: str) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM conversations WHERE conversation_id=?", (conversation_id,))


def build_context_text(context: MemoryContext, max_chars: int = 2400) -> str:
    """在固定字符预算内保留研究状态、旧摘要和最近消息。"""

    structured_sections: list[str] = []
    if context.user_preferences:
        structured_sections.append("用户偏好：" + "；".join(context.user_preferences))
    if context.active_topics:
        structured_sections.append("当前研究主题：" + "；".join(context.active_topics))
    if context.active_papers:
        structured_sections.append("当前关注论文：" + "；".join(context.active_papers))
    structured = "\n".join(structured_sections)
    summary = context.older_summary
    recent = ""
    if context.recent_messages:
        recent = "\n".join(
            f"{('用户' if item['role'] == 'user' else '助手')}：{item['content']}"
            for item in context.recent_messages
        )
        recent = "最近对话：\n" + recent

    if not any((structured, summary, recent)):
        return "无历史对话。"
    if max_chars <= 0:
        return ""

    separator_budget = 2 * max(0, sum(bool(item) for item in (structured, summary, recent)) - 1)
    content_budget = max(0, max_chars - separator_budget)
    structured_budget = content_budget // 4
    summary_budget = content_budget // 4
    recent_budget = content_budget - structured_budget - summary_budget
    selected = [
        structured[:structured_budget],
        summary[-summary_budget:],
        recent[-recent_budget:],
    ]
    return "\n\n".join(part for part in selected if part)
