"""用户级论文库：PDF 文件、页级 Chunk、BM25 检索与强制 Owner 过滤。"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from local_rag.bm25 import BM25Retriever
from local_rag.chunker import FixedWindowChunker
from local_rag.contracts import TextChunk
from local_rag.parser import PyPDFPageParser


class PersonalLibraryStore:
    def __init__(self, db_path: str | Path, files_root: str | Path):
        self.db_path, self.files_root = Path(db_path), Path(files_root)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.files_root.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript("""
            CREATE TABLE IF NOT EXISTS libraries (
                library_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, name TEXT NOT NULL,
                created_at TEXT NOT NULL, UNIQUE(user_id, name)
            );
            CREATE TABLE IF NOT EXISTS library_documents (
                document_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, library_id TEXT NOT NULL,
                title TEXT NOT NULL, filename TEXT NOT NULL, storage_path TEXT NOT NULL,
                sha256 TEXT NOT NULL, page_count INTEGER NOT NULL, chunk_count INTEGER NOT NULL,
                metadata_json TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(user_id, sha256)
            );
            CREATE TABLE IF NOT EXISTS library_chunks (
                chunk_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, library_id TEXT NOT NULL,
                document_id TEXT NOT NULL, page_start INTEGER NOT NULL, page_end INTEGER NOT NULL,
                content TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_library_owner ON library_documents(user_id, library_id);
            CREATE INDEX IF NOT EXISTS idx_chunk_owner ON library_chunks(user_id, library_id);
            """)

    def _connect(self):
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def ensure_default_library(self, user_id: str) -> str:
        with self._connect() as connection:
            row = connection.execute("SELECT library_id FROM libraries WHERE user_id=? AND name='默认论文库'", (user_id,)).fetchone()
            if row:
                return row["library_id"]
            library_id = "L-" + uuid.uuid4().hex[:16]
            connection.execute("INSERT INTO libraries VALUES (?,?,?,?)", (library_id, user_id, "默认论文库", datetime.now(timezone.utc).isoformat()))
            return library_id

    def list_libraries(self, user_id: str) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT l.library_id, l.name, l.created_at, COUNT(d.document_id) AS document_count "
                "FROM libraries l LEFT JOIN library_documents d ON d.library_id=l.library_id "
                "AND d.user_id=l.user_id WHERE l.user_id=? GROUP BY l.library_id "
                "ORDER BY l.created_at, l.name",
                (user_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def create_library(self, user_id: str, name: str) -> dict:
        normalized = name.strip()
        if not normalized:
            raise ValueError("Collection 名称不能为空")
        library_id = "L-" + uuid.uuid4().hex[:16]
        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO libraries VALUES (?,?,?,?)",
                    (library_id, user_id, normalized, datetime.now(timezone.utc).isoformat()),
                )
        except sqlite3.IntegrityError as error:
            raise ValueError("Collection 名称已存在") from error
        return next(item for item in self.list_libraries(user_id) if item["library_id"] == library_id)

    def ingest_pdf(self, user_id: str, filename: str, content: bytes, *, title: str = "", library_id: str = "") -> dict:
        if not content.startswith(b"%PDF"):
            raise ValueError("只允许上传有效 PDF 文件")
        library_id = library_id or self.ensure_default_library(user_id)
        with self._connect() as connection:
            owner = connection.execute("SELECT 1 FROM libraries WHERE library_id=? AND user_id=?", (library_id, user_id)).fetchone()
        if not owner:
            raise PermissionError("论文库不属于当前用户")
        digest = hashlib.sha256(content).hexdigest()
        with self._connect() as connection:
            duplicate = connection.execute("SELECT * FROM library_documents WHERE user_id=? AND sha256=?", (user_id, digest)).fetchone()
        if duplicate:
            return self.get_document(user_id, duplicate["document_id"]) | {"action": "duplicate"}
        safe_name = re.sub(r"[^\w.\-]+", "_", Path(filename).name) or "paper.pdf"
        if not safe_name.casefold().endswith(".pdf"):
            safe_name += ".pdf"
        document_id = "D-" + uuid.uuid4().hex[:16]
        owner_dir = self.files_root / user_id
        owner_dir.mkdir(parents=True, exist_ok=True)
        path = owner_dir / f"{document_id}_{safe_name}"
        path.write_bytes(content)
        try:
            pages = PyPDFPageParser().parse(path, document_id)
            chunks = FixedWindowChunker().chunk(pages)
            now = datetime.now(timezone.utc).isoformat()
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO library_documents VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (document_id, user_id, library_id, title.strip() or Path(safe_name).stem,
                     safe_name, str(path), digest, len(pages), len(chunks), "{}", now),
                )
                connection.executemany(
                    "INSERT INTO library_chunks VALUES (?,?,?,?,?,?,?)",
                    [(chunk.chunk_id, user_id, library_id, document_id, chunk.page_start, chunk.page_end, chunk.text) for chunk in chunks],
                )
        except Exception:
            path.unlink(missing_ok=True)
            raise
        return self.get_document(user_id, document_id) | {"action": "created"}

    def get_document(self, user_id: str, document_id: str) -> dict:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM library_documents WHERE user_id=? AND document_id=?", (user_id, document_id)).fetchone()
        if not row:
            raise KeyError(document_id)
        item = dict(row); item["metadata"] = json.loads(item.pop("metadata_json")); item.pop("storage_path", None)
        return item

    def list_documents(self, user_id: str) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute("SELECT document_id FROM library_documents WHERE user_id=? ORDER BY created_at DESC", (user_id,)).fetchall()
        return [self.get_document(user_id, row["document_id"]) for row in rows]

    def get_document_file(self, user_id: str, document_id: str) -> tuple[Path, str]:
        """返回当前用户拥有的 PDF；数据库路径也必须位于该用户目录内。"""
        with self._connect() as connection:
            row = connection.execute(
                "SELECT storage_path, filename FROM library_documents WHERE user_id=? AND document_id=?",
                (user_id, document_id),
            ).fetchone()
        if not row:
            raise KeyError(document_id)
        path = Path(row["storage_path"]).resolve()
        owner_root = (self.files_root / user_id).resolve()
        if owner_root not in path.parents or not path.is_file():
            raise FileNotFoundError(document_id)
        return path, row["filename"]

    def list_document_chunks(
        self, user_id: str, document_id: str, *, page: int = 1,
        page_size: int = 20, query: str = "",
    ) -> dict:
        """分页读取单篇论文的 Chunk，可按正文关键词过滤且始终校验 Owner。"""
        self.get_document(user_id, document_id)
        page = max(1, page)
        page_size = min(max(1, page_size), 100)
        where = "user_id=? AND document_id=?"
        parameters: list[object] = [user_id, document_id]
        if query.strip():
            where += " AND content LIKE ? ESCAPE '\\'"
            escaped = query.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            parameters.append(f"%{escaped}%")
        with self._connect() as connection:
            total = connection.execute(
                f"SELECT COUNT(*) FROM library_chunks WHERE {where}", parameters,
            ).fetchone()[0]
            rows = connection.execute(
                f"SELECT chunk_id, page_start, page_end, content FROM library_chunks "
                f"WHERE {where} ORDER BY page_start, chunk_id LIMIT ? OFFSET ?",
                [*parameters, page_size, (page - 1) * page_size],
            ).fetchall()
        return {
            "items": [dict(row) for row in rows],
            "page": page,
            "page_size": page_size,
            "total": total,
            "query": query.strip(),
        }

    def update_document(
        self, user_id: str, document_id: str, *, title: str,
        tags: list[str], library_id: str,
    ) -> dict:
        normalized_tags = list(dict.fromkeys(tag.strip() for tag in tags if tag.strip()))[:20]
        with self._connect() as connection:
            collection = connection.execute(
                "SELECT 1 FROM libraries WHERE user_id=? AND library_id=?", (user_id, library_id),
            ).fetchone()
            if not collection:
                raise PermissionError("Collection 不存在或不属于当前用户")
            row = connection.execute(
                "SELECT metadata_json FROM library_documents WHERE user_id=? AND document_id=?",
                (user_id, document_id),
            ).fetchone()
            if not row:
                raise KeyError(document_id)
            metadata = json.loads(row["metadata_json"] or "{}")
            metadata["tags"] = normalized_tags
            connection.execute(
                "UPDATE library_documents SET title=?, library_id=?, metadata_json=? "
                "WHERE user_id=? AND document_id=?",
                (title.strip(), library_id, json.dumps(metadata, ensure_ascii=False), user_id, document_id),
            )
            connection.execute(
                "UPDATE library_chunks SET library_id=? WHERE user_id=? AND document_id=?",
                (library_id, user_id, document_id),
            )
        return self.get_document(user_id, document_id)

    def get_document_file(self, user_id: str, document_id: str) -> tuple[Path, str]:
        """返回当前用户拥有的 PDF；数据库路径也必须位于该用户目录内。"""
        with self._connect() as connection:
            row = connection.execute(
                "SELECT storage_path, filename FROM library_documents WHERE user_id=? AND document_id=?",
                (user_id, document_id),
            ).fetchone()
        if not row:
            raise KeyError(document_id)
        path = Path(row["storage_path"]).resolve()
        owner_root = (self.files_root / user_id).resolve()
        if owner_root not in path.parents or not path.is_file():
            raise FileNotFoundError(document_id)
        return path, row["filename"]

    def list_document_chunks(
        self, user_id: str, document_id: str, *, page: int = 1,
        page_size: int = 20, query: str = "",
    ) -> dict:
        """分页读取单篇论文的 Chunk，可按正文关键词过滤且始终校验 Owner。"""
        self.get_document(user_id, document_id)
        page = max(1, page)
        page_size = min(max(1, page_size), 100)
        where = "user_id=? AND document_id=?"
        parameters: list[object] = [user_id, document_id]
        if query.strip():
            where += " AND content LIKE ? ESCAPE '\\'"
            escaped = query.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            parameters.append(f"%{escaped}%")
        with self._connect() as connection:
            total = connection.execute(
                f"SELECT COUNT(*) FROM library_chunks WHERE {where}", parameters,
            ).fetchone()[0]
            rows = connection.execute(
                f"SELECT chunk_id, page_start, page_end, content FROM library_chunks "
                f"WHERE {where} ORDER BY page_start, chunk_id LIMIT ? OFFSET ?",
                [*parameters, page_size, (page - 1) * page_size],
            ).fetchall()
        return {
            "items": [dict(row) for row in rows],
            "page": page,
            "page_size": page_size,
            "total": total,
            "query": query.strip(),
        }

    def delete_document(self, user_id: str, document_id: str) -> bool:
        with self._connect() as connection:
            row = connection.execute("SELECT storage_path FROM library_documents WHERE user_id=? AND document_id=?", (user_id, document_id)).fetchone()
            if not row:
                return False
            connection.execute("DELETE FROM library_chunks WHERE user_id=? AND document_id=?", (user_id, document_id))
            connection.execute("DELETE FROM library_documents WHERE user_id=? AND document_id=?", (user_id, document_id))
        Path(row["storage_path"]).unlink(missing_ok=True)
        return True

    def search(self, user_id: str, query: str, limit: int = 5) -> dict:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT c.*, d.title, d.filename FROM library_chunks c JOIN library_documents d ON d.document_id=c.document_id WHERE c.user_id=?",
                (user_id,),
            ).fetchall()
        if not rows:
            return {"documents": [], "decision": {"route": "personal_bm25", "candidate_count": 0}}
        chunks = [TextChunk(row["document_id"], row["chunk_id"], row["page_start"], row["page_end"], row["content"], 0, len(row["content"])) for row in rows]
        by_id = {row["chunk_id"]: row for row in rows}
        ranked = BM25Retriever(chunks).search(query, limit)
        documents = [{"title": by_id[chunk.chunk_id]["title"], "authors": [], "year": None,
                      "content": chunk.text, "pdf_url": "", "entry_id": chunk.document_id,
                      "source": "personal_library", "document_id": chunk.document_id,
                      "chunk_id": chunk.chunk_id, "page": chunk.page_start, "retrieval_score": score}
                     for chunk, score in ranked]
        return {"documents": documents, "decision": {"route": "personal_bm25", "candidate_count": len(rows)}}
