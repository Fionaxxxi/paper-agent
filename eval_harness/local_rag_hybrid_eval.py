"""在开发集选择 RRF 参数，并用冻结参数评测独立保留集。"""

from __future__ import annotations

import json
import time
from pathlib import Path

from fastembed import TextEmbedding, __version__ as fastembed_version

from eval_harness.local_rag_dense_eval import MODEL_CONFIGS, _chunks, evaluate_dataset, warm_up_retriever
from local_rag.bm25 import BM25Retriever
from local_rag.dense import DenseIndexCache, DenseRetriever
from local_rag.hybrid import ReciprocalRankFusionRetriever

MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
RRF_CANDIDATES = (20, 40, 60)


def _outcomes(baseline: dict, candidate: dict) -> dict:
    old={case["id"]:case for case in baseline["cases"]}; rows=[]
    for case in candidate["cases"]:
        delta=case["metrics"]["ndcg_at_5"]-old[case["id"]]["metrics"]["ndcg_at_5"]
        rows.append({"id":case["id"],"ndcg_at_5_delta":round(delta,6),"outcome":"improved" if delta>0 else "regressed" if delta<0 else "unchanged"})
    return {name:sum(row["outcome"]==name for row in rows) for name in ("improved","regressed","unchanged")} | {"cases":rows}


def select_candidate(candidates: list[dict]) -> dict:
    return max(candidates,key=lambda item:(item["development"]["summary"]["recall_at_5"],item["development"]["summary"]["ndcg_at_5"],-item["development_outcomes"]["regressed"],-item["development"]["summary"]["average_query_latency_ms"],-item["rrf_k"]))


def run(output_path: Path) -> dict:
    chunks,parser,chunker=_chunks(Path("data/papers"));model=TextEmbedding(MODEL,cache_dir="data/cache/fastembed",local_files_only=True)
    cache=DenseIndexCache(Path("data/cache/local_rag/dense"));fingerprint=cache.fingerprint(chunks,MODEL,f"{parser.name}:{parser.version}",f"{chunker.name}:{chunker.version}");vectors=cache.load(fingerprint,len(chunks))
    if vectors is None: raise RuntimeError("MPNet vector cache is required for controlled Hybrid evaluation")
    dense=DenseRetriever(chunks,model,batch_size=32,vectors=vectors);bm25=BM25Retriever(chunks);warmup=warm_up_retriever(dense)
    dense_development=evaluate_dataset(dense,Path("eval_harness/datasets/rag_gold_v1.json"));candidates=[]
    for rrf_k in RRF_CANDIDATES:
        hybrid=ReciprocalRankFusionRetriever(bm25,dense,rrf_k=rrf_k,candidate_limit=50);development=evaluate_dataset(hybrid,Path("eval_harness/datasets/rag_gold_v1.json"))
        candidates.append({"rrf_k":rrf_k,"development":development,"development_outcomes":_outcomes(dense_development,development)})
    chosen=select_candidate(candidates);chosen_hybrid=ReciprocalRankFusionRetriever(bm25,dense,rrf_k=chosen["rrf_k"],candidate_limit=50)
    dense_holdout=evaluate_dataset(dense,Path("eval_harness/datasets/rag_holdout_v1.json"));hybrid_holdout=evaluate_dataset(chosen_hybrid,Path("eval_harness/datasets/rag_holdout_v1.json"));holdout_outcomes=_outcomes(dense_holdout,hybrid_holdout)
    summary=hybrid_holdout["summary"];base=dense_holdout["summary"]
    decision={"quality_gate_passed":summary["recall_at_5"]>=base["recall_at_5"] and summary["ndcg_at_5"]>base["ndcg_at_5"] and holdout_outcomes["regressed"]<=2,"production_default":False}
    report={"report_version":"1.0","config":{"model":MODEL,"fastembed_version":fastembed_version,"fusion":"rrf","rrf_candidates":list(RRF_CANDIDATES),"candidate_limit":50,"selection_dataset":"development_only","llm_calls":0},"cache":{"hit":True,"fingerprint":fingerprint},"warmup":warmup,"dense_development":dense_development,"candidates":candidates,"selected_rrf_k":chosen["rrf_k"],"dense_holdout":dense_holdout,"hybrid_holdout":hybrid_holdout,"holdout_outcomes":holdout_outcomes,"decision":decision}
    output_path.parent.mkdir(parents=True,exist_ok=True);output_path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8");return report


if __name__=="__main__":
    result=run(Path("outputs/local_rag/hybrid_rrf_eval.json"));print(json.dumps({"selected_rrf_k":result["selected_rrf_k"],"dense":result["dense_holdout"]["summary"],"hybrid":result["hybrid_holdout"]["summary"],"outcomes":result["holdout_outcomes"],"decision":result["decision"]},ensure_ascii=False,indent=2))
