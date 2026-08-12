"""运行本地全文 BM25 基线并保存逐题可审计结果。"""

from __future__ import annotations

import json
import math
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

from eval_harness.rag_eval_models import load_rag_dataset
from local_rag.bm25 import BM25Retriever
from local_rag.chunker import FixedWindowChunker
from local_rag.parser import PyPDFPageParser


def _metrics(ranked_ids: list[str], relevant_ids: set[str], k_values: list[int]) -> dict:
    metrics = {}
    ideal = min(len(relevant_ids), max(k_values))
    for k in k_values:
        top = ranked_ids[:k]
        seen_relevant = set()
        hits = []
        for identity in top:
            is_new_relevant = identity in relevant_ids and identity not in seen_relevant
            hits.append(1 if is_new_relevant else 0)
            if is_new_relevant:
                seen_relevant.add(identity)
        unique_hits = len(set(top) & relevant_ids)
        first = next((rank for rank, hit in enumerate(hits, 1) if hit), 0)
        dcg = sum(hit / math.log2(rank + 1) for rank, hit in enumerate(hits, 1))
        idcg = sum(1 / math.log2(rank + 1) for rank in range(1, min(ideal, k) + 1))
        metrics.update({
            f"recall_at_{k}": round(unique_hits / len(relevant_ids), 6),
            f"mrr_at_{k}": round(1 / first, 6) if first else 0.0,
            f"ndcg_at_{k}": round(dcg / idcg, 6) if idcg else 0.0,
        })
    return metrics


def run_benchmark(papers_dir: Path, dataset_path: Path, output_path: Path, query_transform=None, config_id: str = "bm25-mixed-v1") -> dict:
    dataset = load_rag_dataset(dataset_path)
    sources = json.loads((papers_dir / "corpus_sources.json").read_text(encoding="utf-8"))
    parser, chunker = PyPDFPageParser(), FixedWindowChunker()
    chunks = []
    for source in sources["documents"]:
        chunks.extend(chunker.chunk(parser.parse(papers_dir / source["filename"], source["document_id"])))
    build_started = time.perf_counter()
    retriever = BM25Retriever(chunks)
    build_ms = (time.perf_counter() - build_started) * 1000
    cases, latencies = [], []
    maximum_k = max(dataset.k_values)
    for case in dataset.cases:
        transformed = query_transform(case.question) if query_transform else (case.question, [])
        query, rewrite_matches = transformed
        started = time.perf_counter()
        ranked = retriever.search(query, maximum_k)
        latency_ms = (time.perf_counter() - started) * 1000
        latencies.append(latency_ms)
        relevant_ids = {span.chunk_id for span in case.evidence}
        ranked_ids = [chunk.chunk_id for chunk, _ in ranked]
        metrics = _metrics(ranked_ids, relevant_ids, dataset.k_values)
        relevant_pages = {(span.document_id, span.page_start) for span in case.evidence}
        ranked_pages = [f"{chunk.document_id}:p{chunk.page_start}" for chunk, _ in ranked]
        page_ids = {f"{document_id}:p{page}" for document_id, page in relevant_pages}
        page_metrics = _metrics(ranked_pages, page_ids, dataset.k_values)
        cases.append({
            "id": case.id, "question": case.question, "category": case.category,
            "difficulty": case.difficulty, "latency_ms": round(latency_ms, 4),
            "search_query": query, "rewrite_matches": rewrite_matches,
            "relevant_chunk_ids": sorted(relevant_ids), "metrics": metrics,
            "relevant_page_ids": sorted(page_ids), "page_metrics": page_metrics,
            "first_relevant_rank": next((rank for rank, identity in enumerate(ranked_ids, 1) if identity in relevant_ids), 0),
            "results": [{"rank": rank, "chunk_id": chunk.chunk_id, "document_id": chunk.document_id, "page": chunk.page_start, "score": score, "is_relevant": chunk.chunk_id in relevant_ids, "text_preview": chunk.text[:240]} for rank, (chunk, score) in enumerate(ranked, 1)],
        })
    summary = {"case_count": len(cases), "chunk_count": len(chunks), "index_build_ms": round(build_ms, 3), "average_query_latency_ms": round(statistics.mean(latencies), 4), "p95_query_latency_ms": round(sorted(latencies)[math.ceil(len(latencies) * .95) - 1], 4)}
    for k in dataset.k_values:
        for metric in ("recall", "mrr", "ndcg"):
            key = f"{metric}_at_{k}"
            summary[key] = round(statistics.mean(case["metrics"][key] for case in cases), 6)
            page_key = f"page_{metric}_at_{k}"
            summary[page_key] = round(statistics.mean(case["page_metrics"][key] for case in cases), 6)
    summary["rewritten_case_count"] = sum(bool(case["rewrite_matches"]) for case in cases)
    report = {"report_version": "1.1", "run_at": datetime.now(timezone.utc).isoformat(), "dataset_version": dataset.dataset_version, "corpus_version": dataset.corpus_version, "config": {"config_id": config_id, "retriever_family": "sparse_bm25", "parser": parser.name, "chunker": chunker.name, "tokenizer": "mixed_english_word_chinese_unigram_bigram", "query_transform": "none" if query_transform is None else "deterministic_zh_en_term_expansion_v1", "k1": 1.5, "b": .75, "llm_calls": 0}, "summary": summary, "cases": cases}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    report = run_benchmark(Path("data/papers"), Path("eval_harness/datasets/rag_gold_v1.json"), Path("outputs/local_rag/bm25_baseline.json"))
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
