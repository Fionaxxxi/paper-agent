"""无外部依赖的账号与不透明会话 Token，实现本地 MVP 鉴权。"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _now() -> datetime:
    return datetime.now(timezone.utc)


class IdentityStore:
    def __init__(self, db_path: str | Path, token_ttl_hours: int = 24):
        self.db_path = Path(db_path)
        self.token_ttl_hours = token_ttl_hours
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL, password_salt TEXT NOT NULL,
                display_name TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS auth_sessions (
                token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL,
                created_at TEXT NOT NULL, expires_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            );
            """)

    def _connect(self):
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    @staticmethod
    def _password_hash(password: str, salt: bytes) -> str:
        return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 210_000).hex()

    def register(self, email: str, password: str, display_name: str = "") -> dict:
        normalized = email.strip().casefold()
        if "@" not in normalized or len(password) < 8:
            raise ValueError("邮箱格式无效，且密码至少需要8位")
        salt = secrets.token_bytes(16)
        user_id = "U-" + uuid.uuid4().hex[:16]
        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO users VALUES (?,?,?,?,?,?,?)",
                    (user_id, normalized, self._password_hash(password, salt), salt.hex(),
                     display_name.strip() or normalized.split("@", 1)[0], "active", _now().isoformat()),
                )
        except sqlite3.IntegrityError as error:
            raise ValueError("该邮箱已注册") from error
        return self.get_user(user_id)

    def login(self, email: str, password: str) -> dict:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM users WHERE email=?", (email.strip().casefold(),)).fetchone()
        if not row or row["status"] != "active":
            raise ValueError("邮箱或密码错误")
        actual = self._password_hash(password, bytes.fromhex(row["password_salt"]))
        if not hmac.compare_digest(actual, row["password_hash"]):
            raise ValueError("邮箱或密码错误")
        token = secrets.token_urlsafe(32)
        expires = _now() + timedelta(hours=self.token_ttl_hours)
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO auth_sessions VALUES (?,?,?,?)",
                (hashlib.sha256(token.encode()).hexdigest(), row["user_id"], _now().isoformat(), expires.isoformat()),
            )
        return {"access_token": token, "token_type": "bearer", "expires_at": expires.isoformat(),
                "user": self._public_user(dict(row))}

    def authenticate(self, token: str) -> dict | None:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT u.* FROM auth_sessions s JOIN users u ON u.user_id=s.user_id "
                "WHERE s.token_hash=? AND s.expires_at>? AND u.status='active'",
                (token_hash, _now().isoformat()),
            ).fetchone()
        return self._public_user(dict(row)) if row else None

    def get_user(self, user_id: str) -> dict:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
        if not row:
            raise KeyError(user_id)
        return self._public_user(dict(row))

    @staticmethod
    def _public_user(row: dict) -> dict:
        return {key: row[key] for key in ("user_id", "email", "display_name", "status", "created_at")}
