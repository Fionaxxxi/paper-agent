"""为 LangGraph 主流程提供按需加载的本地全文检索后端。"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from local_rag.bm25 import BM25Retriever
from local_rag.chunker import FixedWindowChunker
from local_rag.dense import DenseIndexCache, DenseRetriever
from local_rag.hybrid import ConfidenceGatedHybridRetriever, ReciprocalRankFusionRetriever
from local_rag.parser import PyPDFPageParser


@lru_cache(maxsize=1)
def build_local_retriever():
    """首次使用时加载 PDF、MPNet 和冻结向量缓存，之后在进程内复用。"""
    from fastembed import TextEmbedding

    papers_dir = Path("data/papers")
    sources = json.loads((papers_dir / "corpus_sources.json").read_text(encoding="utf-8"))
    parser, chunker, chunks = PyPDFPageParser(), FixedWindowChunker(), []
    for source in sources["documents"]:
        chunks.extend(chunker.chunk(parser.parse(papers_dir / source["filename"], source["document_id"])))

    model_name = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
    model = TextEmbedding(model_name, cache_dir="data/cache/fastembed", local_files_only=True)
    cache = DenseIndexCache(Path("data/cache/local_rag/dense"))
    fingerprint = cache.fingerprint(chunks, model_name, f"{parser.name}:{parser.version}", f"{chunker.name}:{chunker.version}")
    vectors = cache.load(fingerprint, len(chunks))
    if vectors is None:
        raise RuntimeError("本地 RAG 向量缓存不存在，请先运行本地 RAG 建库脚本")
    dense = DenseRetriever(chunks, model, batch_size=32, vectors=vectors)
    hybrid = ReciprocalRankFusionRetriever(BM25Retriever(chunks), dense, rrf_k=40, candidate_limit=50)
    return ConfidenceGatedHybridRetriever(dense, hybrid, maximum_dense_top1=.65, maximum_dense_margin=.05)


def search_local_papers(query: str, limit: int = 5) -> dict:
    retriever = build_local_retriever()
    ranked = retriever.search(query, limit)
    manifest = json.loads(Path("data/papers/corpus_sources.json").read_text(encoding="utf-8"))
    metadata = {item["document_id"]: item for item in manifest["documents"]}
    documents = []
    for chunk, score in ranked:
        source = metadata.get(chunk.document_id, {})
        documents.append({
            "title": source.get("title", chunk.document_id),
            "authors": [],
            "year": None,
            "content": chunk.text,
            "pdf_url": source.get("pdf_url", ""),
            "entry_id": source.get("arxiv_id", chunk.document_id),
            "source": "local_rag",
            "document_id": chunk.document_id,
            "chunk_id": chunk.chunk_id,
            "page": chunk.page_start,
            "retrieval_score": score,
        })
    return {"documents": documents, "decision": dict(retriever.last_decision or {})}
