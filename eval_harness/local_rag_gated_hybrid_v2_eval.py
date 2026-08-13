"""在冻结且未见的 holdout v2 上一次性验证置信度门控 Hybrid。"""

from __future__ import annotations

import json
from pathlib import Path

from fastembed import TextEmbedding

from eval_harness.local_rag_dense_eval import _chunks, evaluate_dataset, warm_up_retriever
from eval_harness.local_rag_hybrid_eval import MODEL, _outcomes
from local_rag.bm25 import BM25Retriever
from local_rag.dense import DenseIndexCache, DenseRetriever
from local_rag.hybrid import ConfidenceGatedHybridRetriever, ReciprocalRankFusionRetriever


def run(output_path: Path) -> dict:
    chunks,parser,chunker=_chunks(Path("data/papers"));model=TextEmbedding(MODEL,cache_dir="data/cache/fastembed",local_files_only=True)
    cache=DenseIndexCache(Path("data/cache/local_rag/dense"));fingerprint=cache.fingerprint(chunks,MODEL,f"{parser.name}:{parser.version}",f"{chunker.name}:{chunker.version}");vectors=cache.load(fingerprint,len(chunks))
    if vectors is None: raise RuntimeError("frozen MPNet cache required")
    dense=DenseRetriever(chunks,model,batch_size=32,vectors=vectors);bm25=BM25Retriever(chunks);hybrid=ReciprocalRankFusionRetriever(bm25,dense,rrf_k=40,candidate_limit=50);gated=ConfidenceGatedHybridRetriever(dense,hybrid,.65,.05);warmup=warm_up_retriever(dense)
    dataset=Path("eval_harness/datasets/rag_holdout_v2.json");baseline=evaluate_dataset(dense,dataset)
    # evaluate_dataset 不知道路由决策，因此逐题再次执行冻结门控以记录可审计信号；质量结果来自同一确定性检索器。
    candidate=evaluate_dataset(gated,dataset);decisions=[]
    for case in candidate["cases"]:
        gated.search(case["question"],5);decisions.append({"id":case["id"],**gated.last_decision})
    outcomes=_outcomes(baseline,candidate);b,h=baseline["summary"],candidate["summary"]
    gate_passed=h["recall_at_5"]>=b["recall_at_5"] and h["ndcg_at_5"]>b["ndcg_at_5"] and outcomes["regressed"]<=1 and sum(x["route"]=="hybrid" for x in decisions)>=1
    report={"report_version":"1.1","dataset_role":"frozen_unseen_holdout_v2","config":{"model":MODEL,"rrf_k":40,"maximum_dense_top1":.65,"maximum_dense_margin":.05,"selection_data":"development_v1_only","dense_execution":"reuse_gate_ranking","llm_calls":0},"cache":{"hit":True,"fingerprint":fingerprint},"warmup":warmup,"dense":baseline,"gated_hybrid":candidate,"route_decisions":decisions,"outcomes":outcomes,"decision":{"quality_gate_passed":gate_passed,"production_default":False}}
    output_path.parent.mkdir(parents=True,exist_ok=True);output_path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8");return report


if __name__=="__main__":
    r=run(Path("outputs/local_rag/gated_hybrid_v2_eval.json"));print(json.dumps({"dense":r["dense"]["summary"],"gated":r["gated_hybrid"]["summary"],"routes":r["route_decisions"],"outcomes":r["outcomes"],"decision":r["decision"]},ensure_ascii=False,indent=2))
