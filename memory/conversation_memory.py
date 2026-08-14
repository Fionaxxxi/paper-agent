"""兼容旧调用方式的 SQLite 会话记忆入口。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.config import settings
from memory.structured_memory import MemoryContext, SQLiteMemoryStore, build_context_text


LEGACY_MEMORY_DIR = Path("data/memory")
_default_store: SQLiteMemoryStore | None = None


def get_memory_store() -> SQLiteMemoryStore:
    global _default_store
    expected_path = Path(settings.MEMORY_DB_PATH)
    if _default_store is None or _default_store.db_path != expected_path:
        _default_store = SQLiteMemoryStore(expected_path)
    return _default_store


def _legacy_path(conversation_id: str) -> Path:
    safe_id = conversation_id.replace("/", "_").replace("\\", "_")
    return LEGACY_MEMORY_DIR / f"{safe_id}.json"


def _migrate_legacy_if_needed(conversation_id: str, store: SQLiteMemoryStore) -> None:
    if store.get_messages(conversation_id):
        return
    path = _legacy_path(conversation_id)
    if not path.exists():
        return
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        for message in payload.get("messages", []):
            role = message.get("role")
            if role in {"user", "assistant", "system"}:
                store.append_message(conversation_id, role, message.get("content", ""))
    except (OSError, ValueError, TypeError) as error:
        print(f"[Memory Migration Error] {type(error).__name__}: {error}")


def load_memory_context(conversation_id: str) -> MemoryContext:
    store = get_memory_store()
    _migrate_legacy_if_needed(conversation_id, store)
    return store.load_context(
        conversation_id,
        recent_limit=settings.MEMORY_RECENT_MESSAGES,
        summary_max_chars=settings.MEMORY_SUMMARY_MAX_CHARS,
    )


def load_history(conversation_id: str, max_messages: int = 6) -> list[dict[str, Any]]:
    store = get_memory_store()
    _migrate_legacy_if_needed(conversation_id, store)
    return store.get_messages(conversation_id, limit=max_messages)


def save_message(conversation_id: str, role: str, content: str) -> None:
    store = get_memory_store()
    _migrate_legacy_if_needed(conversation_id, store)
    store.append_message(conversation_id, role, content)


def format_history_text(history: list[dict[str, Any]]) -> str:
    if not history:
        return "无历史对话。"
    lines = []
    for message in history:
        role = message.get("role", "")
        if role in {"user", "assistant"}:
            lines.append(
                f"{('用户' if role == 'user' else '助手')}：{message.get('content', '')}"
            )
    return "\n".join(lines)


def format_memory_context(context: MemoryContext) -> str:
    return build_context_text(context, settings.MEMORY_CONTEXT_MAX_CHARS)


def update_research_memory(
    conversation_id: str,
    *,
    query: str,
    documents: list[dict[str, Any]],
) -> None:
    preferences = []
    if any(marker in query for marker in ("中文", "解释每一步", "详细解释", "简洁")):
        preferences.append(query[:200])
    papers = [str(doc.get("title") or "") for doc in documents[:5]]
    get_memory_store().update_research_context(
        conversation_id,
        preferences=preferences,
        topics=[query[:200]],
        papers=papers,
    )
