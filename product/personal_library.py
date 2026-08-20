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
