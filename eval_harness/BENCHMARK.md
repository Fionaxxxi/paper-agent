# 离线能力基准测试

该基准测试在不调用 LLM、arXiv 或其他网络服务的情况下，将当前实现与明确的旧版策略进行对比。

## 运行方式

```powershell
D:\miniconda3\envs\paper_agent\python.exe -m eval_harness.benchmark
```

默认报告写入：

```text
eval_harness/reports/offline_benchmark.json
```

需要保留多次运行结果时，可以指定其他输出路径：

```powershell
D:\miniconda3\envs\paper_agent\python.exe -m eval_harness.benchmark `
  --output eval_harness/reports/candidate.json
```

## 对比配置

```text
baseline（旧版基线）
├─ 所有输入都被视为研究请求
├─ 检索始终只使用一个查询
├─ 多查询文档只拼接，不执行去重
└─ 检索分数较低时不触发重试

candidate（当前候选实现）
├─ 使用当前 Intent Router（意图路由）
├─ 使用当前规则型 Query Planner（查询规划）
├─ 使用当前 Result Merger（结果合并）
├─ 使用当前检索重试路由
├─ 使用当前 LLM 用量追踪
├─ 使用统一 Tool 协议、执行器和有限恢复
└─ 使用 arXiv + OpenAlex 多源合并、DOI 去重和局部失败恢复
```

## 指标解释

数值越高越好：

- `accuracy_pct`：准确率。
- `plan_accuracy_pct`：查询规划准确率。
- `route_accuracy_pct`：路由准确率。
- `local_response_count`：本地直接响应数量。
- `estimated_llm_calls_avoided`：预计避免的 LLM 调用数量。
- `execution_accuracy_pct`：工具参数、结果、错误和重试行为准确率。
- `structured_error_count`：被转换为标准错误码的失败数量。
- `invalid_input_block_count`：执行前拦截的非法输入数量。
- `invalid_output_block_count`：进入下游前拦截的非法输出数量。
- `permission_block_count`：执行前拒绝的未授权风险工具数量。
- `recovered_retry_count`：通过有限重试恢复的临时失败数量。
- `retrieval_accuracy_pct`：多源覆盖、去重和局部失败恢复场景的整体准确率。
- `provider_call_count`：测试场景中执行的数据源调用总数。
- `partial_failure_recovery_count`：一个来源失败但仍从其他来源取得有效论文的次数。
- `structured_failure_count`：多源流程中保留下来的标准化来源失败数量。

数值越低越好：

- `research_false_block_count`：被错误阻止的研究请求数量。
- `unnecessary_simple_queries`：简单问题产生的多余查询数量。
- `remaining_duplicate_count`：结果合并后剩余的重复文档数量。

需要结合上下文判断：

- `total_planned_queries`：规划查询总数。
- `average_query_count`：平均查询数量。
- `retry_count`：重试次数。
- `documents_removed`：合并时删除的文档数量。

这些指标必须与准确率一起分析。增加查询数量可能提高覆盖率，也可能增加延迟与成本。

真实模型的任务分析和科研答案能力由独立的
`eval_harness/LLM_ONLINE.md` 负责。它不会被本离线命令或普通 pytest 自动触发。

## 当前测试范围

离线基准主要测量确定性的路由和数据处理行为，目前尚不测量：

- 真实模型的输入与输出 Token；
- 答案依据充分程度或幻觉率；
- 在线 arXiv / OpenAlex 的质量、延迟、限流与互补覆盖率（已由独立的 `RETRIEVAL_ONLINE.md` 和在线评测器负责）；
- LLM 最终答案质量；
- 实际货币成本。

这些指标由独立在线评测负责，离线 CI 仍保持稳定且不产生 API 费用。在线结果只有在凭据完整且失败状态被说明后才能用于技术选型。
