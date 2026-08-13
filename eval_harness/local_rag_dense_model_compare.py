"""在冻结语料与指标下比较两个多语言 Dense 模型。"""

from __future__ import annotations

import json
from pathlib import Path


METRICS=("recall_at_1","recall_at_3","recall_at_5","mrr_at_5","ndcg_at_5","page_recall_at_5","page_ndcg_at_5")


def compare(baseline_path:Path,candidate_path:Path,output_path:Path)->dict:
    baseline=json.loads(baseline_path.read_text(encoding="utf-8"));candidate=json.loads(candidate_path.read_text(encoding="utf-8"));splits={}
    for split in ("development","holdout"):
        metrics={key:{"minilm":baseline[split]["summary"][key],"mpnet":candidate[split]["summary"][key],"delta":round(candidate[split]["summary"][key]-baseline[split]["summary"][key],6)} for key in METRICS}
        cases=[]
        for before,after in zip(baseline[split]["cases"],candidate[split]["cases"]):
            if before["id"]!=after["id"]:raise ValueError("case order mismatch")
            delta=round(after["metrics"]["ndcg_at_5"]-before["metrics"]["ndcg_at_5"],6)
            cases.append({"id":before["id"],"minilm_first_rank":before["first_relevant_rank"],"mpnet_first_rank":after["first_relevant_rank"],"ndcg_delta":delta,"outcome":"improved" if delta>0 else "regressed" if delta<0 else "unchanged"})
        splits[split]={"metrics":metrics,"outcomes":{name:sum(x["outcome"]==name for x in cases) for name in ("improved","regressed","unchanged")},"cases":cases,"latency":{"minilm_average_ms":baseline[split]["summary"]["average_query_latency_ms"],"mpnet_average_ms":candidate[split]["summary"]["average_query_latency_ms"]}}
    hold=splits["holdout"];decision={"preferred_model":"mpnet" if hold["metrics"]["ndcg_at_5"]["delta"]>0 and hold["metrics"]["recall_at_5"]["delta"]>=0 and hold["outcomes"]["regressed"]<=2 else "minilm","model_candidate_validated":hold["metrics"]["ndcg_at_5"]["delta"]>0 and hold["metrics"]["recall_at_5"]["delta"]>=0 and hold["outcomes"]["regressed"]<=2,"production_default":False,"next_step":"MPNet 独立进程稳定性或 Hybrid 对照"}
    report={"report_version":"1.0","baseline_config":baseline["config"],"candidate_config":candidate["config"],"splits":splits,"decision":decision};output_path.parent.mkdir(parents=True,exist_ok=True);output_path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8");return report


if __name__=="__main__":print(json.dumps(compare(Path("outputs/local_rag/dense_multilingual_minilm.json"),Path("outputs/local_rag/dense_multilingual_mpnet.json"),Path("outputs/local_rag/dense_model_compare.json")),ensure_ascii=False,indent=2))
