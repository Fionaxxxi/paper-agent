"""多语言 Dense 候选在开发集与独立保留集上的固定评测。"""

from __future__ import annotations

import json
import math
import statistics
import time
from pathlib import Path

from eval_harness.local_rag_benchmark import _metrics
from eval_harness.rag_eval_models import load_rag_dataset
from local_rag.chunker import FixedWindowChunker
from local_rag.dense import DenseIndexCache, DenseRetriever
from local_rag.parser import PyPDFPageParser


MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def _chunks(papers_dir: Path):
    sources = json.loads((papers_dir / "corpus_sources.json").read_text(encoding="utf-8"))
    parser, chunker, chunks = PyPDFPageParser(), FixedWindowChunker(), []
    for source in sources["documents"]:
        chunks.extend(chunker.chunk(parser.parse(papers_dir / source["filename"], source["document_id"])))
    return chunks, parser, chunker


def evaluate_dataset(retriever, dataset_path: Path) -> dict:
    dataset, cases, latencies = load_rag_dataset(dataset_path), [], []
    maximum_k = max(dataset.k_values)
    for case in dataset.cases:
        started = time.perf_counter(); ranked = retriever.search(case.question, maximum_k); latency = (time.perf_counter() - started) * 1000; latencies.append(latency)
        relevant_chunks = {e.chunk_id for e in case.evidence}; ranked_chunks = [chunk.chunk_id for chunk, _ in ranked]
        relevant_pages = {f"{e.document_id}:p{e.page_start}" for e in case.evidence}; ranked_pages = [f"{chunk.document_id}:p{chunk.page_start}" for chunk, _ in ranked]
        metrics, page_metrics = _metrics(ranked_chunks, relevant_chunks, dataset.k_values), _metrics(ranked_pages, relevant_pages, dataset.k_values)
        cases.append({"id": case.id, "question": case.question, "metrics": metrics, "page_metrics": page_metrics, "first_relevant_rank": next((i for i, identity in enumerate(ranked_chunks, 1) if identity in relevant_chunks), 0), "latency_ms": round(latency, 4), "results": [{"rank": rank, "chunk_id": chunk.chunk_id, "document_id": chunk.document_id, "page": chunk.page_start, "score": score, "is_relevant": chunk.chunk_id in relevant_chunks, "text_preview": chunk.text[:240]} for rank, (chunk, score) in enumerate(ranked, 1)]})
    summary = {"case_count": len(cases), "average_query_latency_ms": round(statistics.mean(latencies), 4), "p95_query_latency_ms": round(sorted(latencies)[math.ceil(len(latencies) * .95)-1], 4)}
    for k in dataset.k_values:
        for metric in ("recall", "mrr", "ndcg"):
            key=f"{metric}_at_{k}"; summary[key]=round(statistics.mean(x["metrics"][key] for x in cases),6); summary[f"page_{key}"]=round(statistics.mean(x["page_metrics"][key] for x in cases),6)
    return {"dataset_path": dataset_path.as_posix(), "dataset_version": dataset.dataset_version, "summary": summary, "cases": cases}


def run(output: Path) -> dict:
    from fastembed import TextEmbedding, __version__ as fastembed_version
    papers = Path("data/papers"); chunks, parser, chunker = _chunks(papers)
    model_started=time.perf_counter(); model=TextEmbedding(MODEL_NAME,cache_dir="data/cache/fastembed",local_files_only=True); model_load_ms=(time.perf_counter()-model_started)*1000
    cache=DenseIndexCache(Path("data/cache/local_rag/dense")); fingerprint=cache.fingerprint(chunks,MODEL_NAME,f"{parser.name}:{parser.version}",f"{chunker.name}:{chunker.version}")
    cache_started=time.perf_counter(); vectors=cache.load(fingerprint,len(chunks)); cache_load_ms=(time.perf_counter()-cache_started)*1000; cache_hit=vectors is not None
    index_started=time.perf_counter(); retriever=DenseRetriever(chunks,model,batch_size=32,vectors=vectors); index_ms=(time.perf_counter()-index_started)*1000
    cache_write_ms=0.0
    if not cache_hit:
        write_started=time.perf_counter(); cache.save(fingerprint,retriever.vectors); cache_write_ms=(time.perf_counter()-write_started)*1000
    result={"report_version":"1.1","config":{"config_id":"dense-multilingual-minilm-v1","model":MODEL_NAME,"fastembed_version":fastembed_version,"runtime":"onnxruntime_cpu","pooling":"mean_as_fastembed_0.7.4","dimension":384,"max_tokens":512,"query_prefix":"none","document_prefix":"none","similarity":"l2_normalized_cosine","batch_size":32,"llm_calls":0},"corpus":{"chunk_count":len(chunks),"parser":parser.name,"chunker":chunker.name},"cache":{"version":cache.version,"fingerprint":fingerprint,"hit":cache_hit},"timing":{"model_load_ms":round(model_load_ms,3),"cache_load_ms":round(cache_load_ms,3),"index_build_ms":round(index_ms,3),"cache_write_ms":round(cache_write_ms,3)},"development":evaluate_dataset(retriever,Path("eval_harness/datasets/rag_gold_v1.json")),"holdout":evaluate_dataset(retriever,Path("eval_harness/datasets/rag_holdout_v1.json"))}
    output.parent.mkdir(parents=True,exist_ok=True); output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8"); return result


if __name__ == "__main__":
    result=run(Path("outputs/local_rag/dense_multilingual_minilm.json")); print(json.dumps({"timing":result["timing"],"development":result["development"]["summary"],"holdout":result["holdout"]["summary"]},ensure_ascii=False,indent=2))
