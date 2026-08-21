from __future__ import annotations

import hashlib
from collections import defaultdict

from evolution.models import FailureDataset, StrategyCandidate


ALLOWED_PROPOSALS = {
    "intent_router": ("routing", {"intent_router_candidate": "add_regression_guard"}, "补充失败意图的确定性回归守卫"),
    "clarification": ("few_shot", {"clarification_prompt_candidate": "candidate_examples_v1"}, "为低置信度描述性指代增加候选内示例"),
    "query_planning": ("prompt", {"research_analyzer_prompt_candidate": "few_shot_v1"}, "为计划失败类型生成受限 Prompt 候选"),
    "query_rewrite": ("routing", {"query_rewrite_candidate": "failure_terms_v1"}, "从失败查询提取受审计的改写词候选"),
    "retrieval": ("retrieval", {"local_rag_candidate": {"top_k": 8}}, "扩大候选召回但保留最终 Top-K 与成本门控"),
    "research_coverage": ("policy", {"coverage_candidate": "entity_pair_guard_v1"}, "加强比较任务双方实体覆盖检查"),
    "tool_execution": ("policy", {"tool_policy_candidate": "error_specific_retry_v1"}, "根据结构化错误码生成有限重试候选"),
    "citation_validation": ("prompt", {"citation_prompt_candidate": "evidence_id_examples_v1"}, "补充 Evidence ID 引用格式候选"),
    "claim_evidence_validation": ("prompt", {"claim_validator_candidate": "strict_entailment_v1"}, "收紧声明与证据蕴含约束"),
    "pdf_grounding": ("prompt", {"pdf_grounding_candidate": "uncertainty_guard_v1"}, "加强页码和视觉不确定性披露"),
    "answer_verification": ("prompt", {"answer_prompt_candidate": "failure_targeted_v1"}, "根据验证失败生成一次定向修复候选"),
    "memory": ("policy", {"memory_value_threshold_candidate": 0.8}, "提高长期记忆候选写入门槛"),
}


def generate_candidates(dataset: FailureDataset, max_candidates: int = 5) -> list[StrategyCandidate]:
    grouped: dict[str, list] = defaultdict(list)
    for record in dataset.records:
        grouped[record.module].append(record)
    ordered = sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0]))
    candidates: list[StrategyCandidate] = []
    for module, records in ordered:
        proposal = ALLOWED_PROPOSALS.get(module)
        if proposal is None:
            continue
        change_type, config_patch, rationale = proposal
        case_ids = list(dict.fromkeys(record.case_id for record in records))
        digest = hashlib.sha256(f"{module}:{','.join(case_ids)}".encode()).hexdigest()[:10]
        risk = "high" if any(record.severity == "critical" for record in records) else "medium"
        candidates.append(StrategyCandidate(
            candidate_id=f"candidate-{module}-{digest}",
            target_module=module,
            change_type=change_type,
            config_patch=config_patch,
            rationale=f"{rationale}；依据 {len(case_ids)} 个失败 Case",
            evidence_case_ids=case_ids,
            risk_level=risk,
        ))
        if len(candidates) >= max_candidates:
            break
    return candidates
