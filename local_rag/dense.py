"""可替换 Embedding 后端的本地余弦 Dense 检索器。"""

from __future__ import annotations

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

    def __init__(self, chunks: list[TextChunk], embedding_backend, batch_size: int = 64):
        if not chunks or batch_size < 1:
            raise ValueError("require chunks and positive batch_size")
        self.chunks, self.embedding_backend = chunks, embedding_backend
        vectors = list(embedding_backend.embed([chunk.text for chunk in chunks], batch_size=batch_size))
        if len(vectors) != len(chunks):
            raise ValueError("embedding count must match chunk count")
        self.vectors = _normalize(np.asarray(vectors))

    def search(self, query: str, limit: int = 5) -> list[tuple[TextChunk, float]]:
        if limit < 1:
            raise ValueError("limit must be positive")
        query_vector = _normalize(np.asarray(list(self.embedding_backend.embed([query]))))[0]
        scores = self.vectors @ query_vector
        order = sorted(range(len(self.chunks)), key=lambda index: (-float(scores[index]), self.chunks[index].document_id, self.chunks[index].chunk_id))[:limit]
        return [(self.chunks[index], round(float(scores[index]), 8)) for index in order]
