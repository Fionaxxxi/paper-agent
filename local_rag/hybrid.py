"""使用倒数排名融合（RRF）的可审计 BM25 + Dense 检索器。"""

from __future__ import annotations

from local_rag.contracts import TextChunk


class ReciprocalRankFusionRetriever:
    name = "bm25_dense_rrf"
    version = "1.0"

    def __init__(self, bm25, dense, rrf_k: int = 60, candidate_limit: int = 50):
        if rrf_k < 1 or candidate_limit < 1:
            raise ValueError("rrf_k and candidate_limit must be positive")
        self.bm25, self.dense, self.rrf_k, self.candidate_limit = bm25, dense, rrf_k, candidate_limit

    def search(self, query: str, limit: int = 5) -> list[tuple[TextChunk, float]]:
        if limit < 1:
            raise ValueError("limit must be positive")
        pool = max(limit, self.candidate_limit)
        sources = (self.bm25.search(query, pool), self.dense.search(query, pool))
        chunks, scores, best_rank = {}, {}, {}
        for ranked in sources:
            for rank, (chunk, _source_score) in enumerate(ranked, 1):
                identity = chunk.chunk_id
                chunks[identity] = chunk
                scores[identity] = scores.get(identity, 0.0) + 1.0 / (self.rrf_k + rank)
                best_rank[identity] = min(best_rank.get(identity, rank), rank)
        order = sorted(chunks, key=lambda identity: (-scores[identity], best_rank[identity], chunks[identity].document_id, identity))[:limit]
        return [(chunks[identity], round(scores[identity], 8)) for identity in order]
