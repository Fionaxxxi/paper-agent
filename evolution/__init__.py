"""受控策略进化：失败归因、候选生成、晋升门控与版本审计。"""

from evolution.candidate_generator import generate_candidates
from evolution.failure_dataset import build_failure_dataset
from evolution.promotion_gate import evaluate_promotion
from evolution.registry import StrategyVersionRegistry

__all__ = [
    "StrategyVersionRegistry",
    "build_failure_dataset",
    "evaluate_promotion",
    "generate_candidates",
]
