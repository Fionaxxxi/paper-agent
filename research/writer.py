"""Research Writer 的证据约束与无模型降级输出。"""

from __future__ import annotations

import json
from typing import Any


def build_writer_prompt(base_prompt: str, state: dict[str, Any]) -> str:
    store = state.get("evidence_store", {})
    coverage = state.get("research_coverage", {})
    evidence = [
        {
            "evidence_id": item.get("evidence_id"),
            "title": item.get("title"),
            "source": item.get("source"),
            "locator": item.get("locator"),
            "snippet": item.get("snippet"),
            "task_ids": item.get("task_ids", []),
        }
        for item in store.get("evidence", [])
    ]
    return f"""{base_prompt}

【Research Writer 证据约束】
证据覆盖状态：{coverage.get('status', 'unknown')}
覆盖率：{coverage.get('coverage_pct', 0.0)}%
未覆盖声明：{json.dumps(coverage.get('uncovered_claims', []), ensure_ascii=False)}

【可引用证据清单】
{json.dumps(evidence, ensure_ascii=False, indent=2)}

写作规则：
- 重要事实必须使用 `[E-xxxxxxxxxxxx]` 标注对应 evidence_id；
- 只能使用上方清单中真实存在的 evidence_id，不得创造引用；
- 对未覆盖声明必须写“证据不足”，不得补写确定性结论；
- 报告末尾增加“证据索引”，列出 evidence_id、论文标题和 locator；
- 综合判断要明确标记为“综合判断”，不能伪装成单篇论文原结论。
"""


def build_coverage_blocked_answer(state: dict[str, Any]) -> str:
    coverage = state.get("research_coverage", {})
    missing = coverage.get("uncovered_claims", [])
    missing_lines = "\n".join(
        f"- {item.get('claim') or item.get('task_id')}：缺少任务 "
        f"{', '.join(item.get('missing_dependency_task_ids', [])) or '对应证据'}"
        for item in missing
    ) or "- 当前研究计划没有形成可验证的综合证据"
    return f"""## 研究报告生成已降级

检索结果不足以支持计划中的核心综合结论，因此 Research Writer 未调用大模型，避免生成无依据报告。

### 未覆盖的研究结论

{missing_lines}

### 建议

请缩小研究范围、补充论文名称或时间条件，或在论文数据源恢复后重新检索。
"""
