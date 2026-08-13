"""评估仅依赖运行时可见信号的 Hybrid 门控，不允许使用主题或用例身份。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GateRule:
    maximum_dense_top1: float
    maximum_dense_margin: float
    minimum_overlap: float

    def triggers(self, feature: dict) -> bool:
        return feature["dense_top1"] <= self.maximum_dense_top1 and feature["dense_margin"] <= self.maximum_dense_margin and feature["top5_overlap"] >= self.minimum_overlap


def extract_features(dense_case: dict, bm25_case: dict) -> dict:
    dense_scores=[item["score"] for item in dense_case["results"]]
    dense_ids=[item["chunk_id"] for item in dense_case["results"][:5]];bm25_ids=[item["chunk_id"] for item in bm25_case["results"][:5]]
    return {"dense_top1":dense_scores[0],"dense_margin":round(dense_scores[0]-dense_scores[1],8),"top5_overlap":len(set(dense_ids)&set(bm25_ids))/5}


def audit_rules(rows: list[dict], rules: list[GateRule]) -> dict:
    candidates=[]
    for rule in rules:
        triggered=[row for row in rows if rule.triggers(row["features"])]
        improved=sum(row["outcome"]=="improved" for row in triggered);regressed=sum(row["outcome"]=="regressed" for row in triggered)
        leave_one_out_safe=all(not any(rule.triggers(other["features"]) and other["outcome"]=="regressed" for j,other in enumerate(rows) if j!=i) for i in range(len(rows)))
        candidates.append({"rule":rule,"triggered":len(triggered),"improved":improved,"regressed":regressed,"leave_one_out_safe":leave_one_out_safe})
    eligible=[x for x in candidates if x["improved"]>=2 and x["regressed"]==0 and x["leave_one_out_safe"]]
    return {"gate_learnable":bool(eligible),"selected":max(eligible,key=lambda x:(x["improved"],-x["triggered"])) if eligible else None,"candidates":candidates}
