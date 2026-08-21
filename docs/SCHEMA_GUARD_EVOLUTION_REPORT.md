# Research Analyzer Schema Guard 真实进化测试

测试日期：2026-08-21  
模型：`qwen3.7-max-2026-05-17`  
基线：zero-shot  
候选：zero-shot + 最小 JSON Schema Guard  
冻结数据集：6 个 L3 研究问题

## 1. 候选修改

没有加入 Few-shot 示例，只补充以下类型约束：

- `objectives`、`evaluation_dimensions`、`source_requirements`、`secondary_skills` 必须是 JSON 数组；
- 单值也必须使用数组；
- 布尔字段必须为 JSON Boolean；
- `confidence` 必须为 0—1 数值。

该候选针对上一轮真实出现的 `source_requirements` 字符串导致 Pydantic 解析失败问题。

## 2. 真实 A/B 结果

| 指标 | zero-shot | Schema Guard | 变化 |
|---|---:|---:|---:|
| 解析率 | 50.00% | 100.00% | +50.00pp |
| 能力通过率 | 16.67% | 16.67% | 0pp |
| 总 Token | 7,221 | 8,086 | +865 |
| 平均 Token/题 | 1,203.50 | 1,347.67 | +11.98% |
| 平均延迟 | 9.43s | 8.38s | -1.05s |
| P95 延迟 | 14.34s | 10.64s | -25.76% |
| Provider Failure | 0 | 0 | 无变化 |

真实调用 12 次，总 Token 15,307。

## 3. 逐题结果

| Case | zero-shot | Schema Guard | 变化 |
|---|---|---|---|
| `time_trend_gap` | 解析失败 | 失败 | 修复格式，维度仍不足 |
| `architecture_value` | 失败 | 失败 | 无能力提升 |
| `compare_research_value` | 失败 | 失败 | 无能力提升 |
| `multi_dimension_architecture` | 解析失败 | 失败 | 修复格式，语义仍不足 |
| `graphrag_open_problems` | 通过 | 通过 | 保持稳定 |
| `self_evolution` | 解析失败 | 失败 | 修复格式，维度仍不足 |

## 4. Promotion Gate

```text
status = rejected
blockers = insufficient_quality_gain, token_budget_exceeded
regressed_case_ids = []
auto_applied = false
```

拒绝原因：

1. 通过率没有提升，未达到至少 +2 个百分点门槛。
2. 平均 Token 增加 11.98%，略高于 10% 上限。

正面结果：没有逐题回归，P95 延迟下降，结构化解析率达到 100%。但“格式更稳定”不能替代“研究语义判断更准确”。

## 5. 与完整 Few-shot 候选对比

| 候选 | 解析效果 | 能力效果 | 成本 | 回归 | Gate |
|---|---|---|---|---|---|
| 完整 Few-shot | 100% | 66.67% | +28.92% | 1 个 | 拒绝 |
| 最小 Schema Guard | 100% | 16.67% | +11.98% | 0 个 | 拒绝 |

完整 Few-shot 有语义收益但成本高且回归；Schema Guard 修复格式且不回归，但没有语义收益。两者都不满足晋升条件。

## 6. 当前生产决策

继续保留 `zero_shot`。Schema Guard 作为失败实验保存在版本和报告中，不写入 `.env`，不切换 active version。

如果未来继续，候选应针对 objective/dimension coverage 做短规则补全，优先复用 `enforce_analysis_policy`，而不是继续增加 Prompt 示例。该方向可离线实现并先用现有原始输出重判，减少真实模型调用。

## 7. 测试产物

- `outputs/research_analyzer_prompt_ab/schema_guard/latest_analyzer_prompt_ab_online.json`
- `outputs/research_analyzer_prompt_ab/schema_guard/latest_analyzer_prompt_ab_online.csv`
- `outputs/evolution/real_schema_guard/latest_evolution_report.json`
- `outputs/evolution/real_schema_guard/real_scorecards.json`
- `outputs/test_reports/schema_guard_evolution/latest_test_details.csv`

相关离线回归为 21/21 通过，0 LLM。
