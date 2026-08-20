"""官方 LangGraph SqliteSaver 的项目生命周期封装。"""

from __future__ import annotations

import atexit
import sqlite3
import threading
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver


_LOCK = threading.Lock()
_DEFAULT_SAVER: SqliteSaver | None = None
_DEFAULT_CONNECTION: sqlite3.Connection | None = None
_DEFAULT_PATH: Path | None = None


def create_sqlite_checkpointer(
    db_path: str | Path, *, enabled: bool = True
) -> SqliteSaver | None:
    if not enabled:
        return None
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, check_same_thread=False)
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA foreign_keys = ON")
    return SqliteSaver(connection)


def get_default_graph_checkpointer(
    db_path: str | Path, *, enabled: bool = True
) -> SqliteSaver | None:
    global _DEFAULT_SAVER, _DEFAULT_CONNECTION, _DEFAULT_PATH
    if not enabled:
        return None
    path = Path(db_path)
    with _LOCK:
        if _DEFAULT_SAVER is not None and _DEFAULT_PATH == path:
            return _DEFAULT_SAVER
        if _DEFAULT_CONNECTION is not None:
            _DEFAULT_CONNECTION.close()
        path.parent.mkdir(parents=True, exist_ok=True)
        _DEFAULT_CONNECTION = sqlite3.connect(path, check_same_thread=False)
        _DEFAULT_CONNECTION.execute("PRAGMA journal_mode = WAL")
        _DEFAULT_CONNECTION.execute("PRAGMA foreign_keys = ON")
        _DEFAULT_SAVER = SqliteSaver(_DEFAULT_CONNECTION)
        _DEFAULT_PATH = path
        return _DEFAULT_SAVER


def close_default_graph_checkpointer() -> None:
    global _DEFAULT_SAVER, _DEFAULT_CONNECTION, _DEFAULT_PATH
    with _LOCK:
        if _DEFAULT_CONNECTION is not None:
            _DEFAULT_CONNECTION.close()
        _DEFAULT_SAVER = None
        _DEFAULT_CONNECTION = None
        _DEFAULT_PATH = None


def delete_thread_checkpoints(thread_id: str) -> int:
    """删除当前默认 SqliteSaver 中属于指定 thread 的检查点。"""
    if not thread_id or _DEFAULT_CONNECTION is None:
        return 0
    deleted = 0
    with _LOCK:
        for table in ("checkpoint_writes", "checkpoint_blobs", "checkpoints"):
            exists = _DEFAULT_CONNECTION.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
            ).fetchone()
            if exists:
                cursor = _DEFAULT_CONNECTION.execute(
                    f"DELETE FROM {table} WHERE thread_id=?", (thread_id,)
                )
                deleted += max(cursor.rowcount, 0)
        _DEFAULT_CONNECTION.commit()
    return deleted


atexit.register(close_default_graph_checkpointer)
