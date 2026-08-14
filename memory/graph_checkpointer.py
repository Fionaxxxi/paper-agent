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


atexit.register(close_default_graph_checkpointer)
