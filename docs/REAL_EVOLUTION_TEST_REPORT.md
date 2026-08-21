# PaperAgent 受控策略进化真实在线测试报告

测试日期：2026-08-21  
模型：`qwen3.7-max-2026-05-17`  
候选：Research Analyzer `few_shot`  
基线：Research Analyzer `zero_shot`  
数据集：冻结的 `research_analyzer_prompt_ab_v1`，6 个 L3 研究问题

## 1. 测试目的

验证受控策略进化不是只会读取演示分数，而是可以使用当前真实模型输出完成：

```text
同一冻结集真实 A/B
→ 保存逐题输出、Token 和延迟
→ 生成真实 Scorecard
→ 检查逐题回归
→ Promotion Gate
→ 接受或拒绝候选
```

本轮共调用模型 12 次：6 个问题分别运行 zero-shot 和 few-shot。

## 2. 真实 A/B 结果

| 指标 | zero-shot 基线 | few-shot 候选 | 变化 |
|---|---:|---:|---:|
| 结构化解析率 | 66.67% | 100.00% | +33.33 个百分点 |
| 能力通过率 | 16.67% | 66.67% | +50.00 个百分点 |
| 总 Token | 7,055 | 9,095 | +2,040 |
| 平均 Token/Case | 1,175.83 | 1,515.83 | +28.92% |
| 平均延迟 | 9.64s | 11.37s | +1.73s |
| P95 延迟 | 12.20s | 13.69s | +12.22% |
| Provider Failure | 0 | 0 | 无变化 |

总调用 12 次，总 Token 16,150。

## 3. 逐题结果

| Case | zero-shot | few-shot | 结论 |
|---|---|---|---|
| `time_trend_gap` | 失败 | 通过 | 候选修复趋势维度覆盖 |
| `architecture_value` | 失败 | 通过 | 候选保留代表论文目标 |
| `compare_research_value` | 失败 | 通过 | 候选正确选择 Literature Review Skill |
| `multi_dimension_architecture` | 解析失败 | 通过 | 候选输出符合结构化 Contract |
| `graphrag_open_problems` | 通过 | 失败 | **已有能力回归：dimension coverage** |
| `self_evolution` | 解析失败 | 失败 | 解析修复，但评测维度覆盖仍不足 |

zero-shot 的两个解析失败都来自 `source_requirements` 返回字符串而 Contract 要求列表。few-shot 修复了这类格式问题。

## 4. Promotion Gate 结果

```text
status = rejected
gate_passed = false
auto_applied = false
```

阻断原因：

1. `case_regression`：`graphrag_open_problems` 从通过退化为失败。
2. `token_budget_exceeded`：平均 Token 增加 28.92%，超过 10% 门槛。

警告：

- `latency_increased`：P95 延迟增加 12.22%，尚未超过 15% 硬门槛。

## 5. 最终决策

**不晋升 few-shot，继续保留 zero-shot 为当前生产策略。**

虽然候选总体通过率明显提高，但受控进化不允许用平均分掩盖原本通过 Case 的退化，也不接受超过成本预算的候选。这正是 Promotion Gate 相比“只看总体准确率”的价值。

## 6. 下一候选应如何优化

不直接采用完整 few-shot，而应产生更小候选：

- 保留 zero-shot 主体；
- 只增加 `source_requirements` 必须为 JSON List 的最小格式示例；
- 不增加可能改变维度选择的完整研究案例；
- 针对 `graphrag_open_problems` 和 `self_evolution` 增加冻结回归；
- 重新运行同一 6 题 A/B，要求零逐题回归、Token 增幅不超过 10%。

本轮按用户要求完成真实测试后停止，不自动继续生成并付费测试第二个候选。

后续经用户要求已继续测试第二个最小候选 Schema Guard。它将解析率提升到 100% 且无逐题回归，但能力通过率没有提升、Token 增加 11.98%，仍被 Gate 拒绝。详见 [Schema Guard 真实进化测试](SCHEMA_GUARD_EVOLUTION_REPORT.md)。

## 7. 产物

- `outputs/research_analyzer_prompt_ab/latest_analyzer_prompt_ab_online.json`
- `outputs/research_analyzer_prompt_ab/latest_analyzer_prompt_ab_online.csv`
- `outputs/evolution/real_analyzer_ab/latest_evolution_report.json`
- `outputs/evolution/real_analyzer_ab/latest_evolution_failures.csv`
- `outputs/evolution/real_analyzer_ab/latest_evolution_candidates.csv`
- `outputs/evolution/real_analyzer_ab/real_scorecards.json`

离线适配和 Gate 回归：10/10 通过，0 LLM。测试说明表位于 `outputs/test_reports/controlled_evolution_real/latest_test_details.csv`。
