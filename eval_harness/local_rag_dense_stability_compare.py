"""比较 MiniLM 与 MPNet 的独立进程稳定性，不覆盖各自原始判定。"""

from __future__ import annotations

import json
from pathlib import Path


def compare(minilm_path: Path, mpnet_path: Path, output_path: Path) -> dict:
    minilm=json.loads(minilm_path.read_text(encoding="utf-8"));mpnet=json.loads(mpnet_path.read_text(encoding="utf-8"))
    metrics={}
    for key in minilm["timing"]:
        metrics[key]={"minilm_mean":minilm["timing"][key]["mean"],"minilm_cv":minilm["timing"][key]["cv"],"mpnet_mean":mpnet["timing"][key]["mean"],"mpnet_cv":mpnet["timing"][key]["cv"],"mean_ratio":round(mpnet["timing"][key]["mean"]/minilm["timing"][key]["mean"],4)}
    report={"report_version":"1.0","metrics":metrics,"determinism":{"minilm":minilm["quality_equal"] and minilm["top5_rankings_equal"] and minilm["scores_equal"],"mpnet":mpnet["quality_equal"] and mpnet["top5_rankings_equal"] and mpnet["scores_equal"]},"decision":{"minilm_stability_validated":minilm["decision"]["stability_validated"],"mpnet_stability_validated":mpnet["decision"]["stability_validated"],"production_default":False,"next_step":"隔离首次查询预热后重新评测 MPNet 性能稳定性"}}
    output_path.parent.mkdir(parents=True,exist_ok=True);output_path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8");return report


if __name__=="__main__":print(json.dumps(compare(Path("outputs/local_rag/dense_stability.json"),Path("outputs/local_rag/mpnet_stability.json"),Path("outputs/local_rag/dense_stability_model_compare.json")),ensure_ascii=False,indent=2))
