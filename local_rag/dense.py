"""可替换 Embedding 后端的本地余弦 Dense 检索器。"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import numpy as np

from local_rag.contracts import TextChunk


def _normalize(matrix: np.ndarray) -> np.ndarray:
    matrix = np.asarray(matrix, dtype=np.float32)
    if matrix.ndim == 1:
        matrix = matrix.reshape(1, -1)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    if np.any(norms == 0):
        raise ValueError("embedding vectors must be non-zero")
    return matrix / norms


class DenseRetriever:
    name = "dense_cosine"
    version = "1.0"

    def __init__(self, chunks: list[TextChunk], embedding_backend, batch_size: int = 64, vectors: np.ndarray | None = None):
        if not chunks or batch_size < 1:
            raise ValueError("require chunks and positive batch_size")
        self.chunks, self.embedding_backend = chunks, embedding_backend
        if vectors is None:
            vectors = np.asarray(list(embedding_backend.embed([chunk.text for chunk in chunks], batch_size=batch_size)))
        if len(vectors) != len(chunks):
            raise ValueError("embedding count must match chunk count")
        self.vectors = _normalize(vectors)

    def search(self, query: str, limit: int = 5) -> list[tuple[TextChunk, float]]:
        if limit < 1:
            raise ValueError("limit must be positive")
        query_vector = _normalize(np.asarray(list(self.embedding_backend.embed([query]))))[0]
        scores = self.vectors @ query_vector
        order = sorted(range(len(self.chunks)), key=lambda index: (-float(scores[index]), self.chunks[index].document_id, self.chunks[index].chunk_id))[:limit]
        return [(self.chunks[index], round(float(scores[index]), 8)) for index in order]


class DenseIndexCache:
    """以语料、处理版本和模型配置指纹保护的可重建向量缓存。"""

    version = "1.0"

    def __init__(self, cache_dir: Path):
        self.cache_dir = Path(cache_dir)

    @staticmethod
    def fingerprint(chunks: list[TextChunk], model_name: str, parser_version: str, chunker_version: str) -> str:
        digest = hashlib.sha256()
        config = {"cache_version": DenseIndexCache.version, "model": model_name, "parser": parser_version, "chunker": chunker_version}
        digest.update(json.dumps(config, sort_keys=True, separators=(",", ":")).encode())
        for chunk in chunks:
            digest.update(json.dumps([chunk.document_id, chunk.chunk_id, chunk.page_start, chunk.page_end, chunk.char_start, chunk.char_end, chunk.text], ensure_ascii=False, separators=(",", ":")).encode())
        return digest.hexdigest()

    def load(self, fingerprint: str, expected_count: int) -> np.ndarray | None:
        metadata_path, vectors_path = self.cache_dir / f"{fingerprint}.json", self.cache_dir / f"{fingerprint}.npy"
        if not metadata_path.is_file() or not vectors_path.is_file():
            return None
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            vectors = np.load(vectors_path, allow_pickle=False)
        except (OSError, ValueError, json.JSONDecodeError):
            return None
        if metadata != {"cache_version": self.version, "fingerprint": fingerprint, "chunk_count": expected_count, "dimension": int(vectors.shape[1]) if vectors.ndim == 2 else 0}:
            return None
        if vectors.ndim != 2 or len(vectors) != expected_count or not np.isfinite(vectors).all():
            return None
        return _normalize(vectors)

    def save(self, fingerprint: str, vectors: np.ndarray) -> tuple[Path, Path]:
        vectors = _normalize(vectors).astype(np.float32)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        vectors_path, metadata_path = self.cache_dir / f"{fingerprint}.npy", self.cache_dir / f"{fingerprint}.json"
        temporary = vectors_path.with_suffix(".npy.tmp")
        with temporary.open("wb") as stream:
            np.save(stream, vectors, allow_pickle=False)
        os.replace(temporary, vectors_path)
        metadata = {"cache_version": self.version, "fingerprint": fingerprint, "chunk_count": len(vectors), "dimension": int(vectors.shape[1])}
        metadata_tmp = metadata_path.with_suffix(".json.tmp")
        metadata_tmp.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(metadata_tmp, metadata_path)
        return vectors_path, metadata_path
