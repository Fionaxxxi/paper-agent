"""使用倒数排名融合（RRF）的可审计 BM25 + Dense 检索器。"""

from __future__ import annotations

from collections.abc import Sequence

from local_rag.contracts import TextChunk

RankedResults = Sequence[tuple[TextChunk, float]]


class ReciprocalRankFusionRetriever:
    name = "bm25_dense_rrf"
    version = "1.1"

    def __init__(self, bm25, dense, rrf_k: int = 60, candidate_limit: int = 50):
        if rrf_k < 1 or candidate_limit < 1:
            raise ValueError("rrf_k and candidate_limit must be positive")
        self.bm25 = bm25
        self.dense = dense
        self.rrf_k = rrf_k
        self.candidate_limit = candidate_limit

    def _fuse(self, sources: Sequence[RankedResults], limit: int) -> list[tuple[TextChunk, float]]:
        chunks: dict[str, TextChunk] = {}
        scores: dict[str, float] = {}
        best_rank: dict[str, int] = {}
        for ranked in sources:
            for rank, (chunk, _source_score) in enumerate(ranked, 1):
                identity = chunk.chunk_id
                chunks[identity] = chunk
                scores[identity] = scores.get(identity, 0.0) + 1.0 / (self.rrf_k + rank)
                best_rank[identity] = min(best_rank.get(identity, rank), rank)
        order = sorted(
            chunks,
            key=lambda identity: (
                -scores[identity],
                best_rank[identity],
                chunks[identity].document_id,
                identity,
            ),
        )[:limit]
        return [(chunks[identity], round(scores[identity], 8)) for identity in order]

    def search_with_dense(
        self,
        query: str,
        dense_results: RankedResults,
        limit: int = 5,
    ) -> list[tuple[TextChunk, float]]:
        """复用已经计算的 Dense 排名，只补充 BM25 并执行 RRF。"""
        if limit < 1:
            raise ValueError("limit must be positive")
        pool = max(limit, self.candidate_limit)
        bm25_results = self.bm25.search(query, pool)
        return self._fuse((bm25_results, dense_results[:pool]), limit)

    def search(self, query: str, limit: int = 5) -> list[tuple[TextChunk, float]]:
        if limit < 1:
            raise ValueError("limit must be positive")
        pool = max(limit, self.candidate_limit)
        dense_results = self.dense.search(query, pool)
        return self.search_with_dense(query, dense_results, limit)


class ConfidenceGatedHybridRetriever:
    """Dense 默认路径；仅在低置信度且小间隔时触发 Hybrid。"""

    name = "confidence_gated_bm25_dense_rrf"
    version = "1.1"

    def __init__(
        self,
        dense,
        hybrid: ReciprocalRankFusionRetriever,
        maximum_dense_top1: float = 0.65,
        maximum_dense_margin: float = 0.05,
    ):
        self.dense = dense
        self.hybrid = hybrid
        self.maximum_dense_top1 = maximum_dense_top1
        self.maximum_dense_margin = maximum_dense_margin
        self.last_decision = None

    def search(self, query: str, limit: int = 5) -> list[tuple[TextChunk, float]]:
        if limit < 1:
            raise ValueError("limit must be positive")
        pool = max(limit, 2, self.hybrid.candidate_limit)
        dense_results = self.dense.search(query, pool)
        if len(dense_results) < 2:
            raise RuntimeError("confidence gate requires at least two dense results")
        top1 = dense_results[0][1]
        margin = top1 - dense_results[1][1]
        triggered = top1 <= self.maximum_dense_top1 and margin <= self.maximum_dense_margin
        self.last_decision = {
            "route": "hybrid" if triggered else "dense",
            "dense_top1": top1,
            "dense_margin": round(margin, 8),
            "thresholds": {
                "maximum_dense_top1": self.maximum_dense_top1,
                "maximum_dense_margin": self.maximum_dense_margin,
            },
        }
        if triggered:
            return self.hybrid.search_with_dense(query, dense_results, limit)
        return list(dense_results[:limit])
