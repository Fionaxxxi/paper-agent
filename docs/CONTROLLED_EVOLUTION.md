# PaperAgent 受控策略进化 v1

更新日期：2026-08-21  
定位：基于评测反馈的受控 Agent 策略进化，不是模型权重训练，也不是 Agent 自动修改生产代码。

## 1. 解决的问题

普通 Agent 开发往往是：发现错误后人工改 Prompt，再凭几个 Demo 判断是否变好。这样容易出现局部修复、整体退化，也缺少版本和回滚记录。

PaperAgent 的进化闭环将改进过程变成可审计流水线：

```text
Eval / Trace / Badcase
→ Failure Dataset
→ Failure Attribution
→ Strategy Candidate Generator
→ 同一冻结集 Baseline / Candidate Scorecard
→ Promotion Gate
→ Version Registry
→ eligible / reject
→ 人工审批后才允许真正应用
```

## 2. 当前实现的四个核心模块

### 2.1 Failure Dataset

输入已有 JSON/JSONL 评测报告，识别 `cases/rows/results/records`，提取：

- `case_id`、`trace_id` 和原问题；
- `failure_type` 和严重程度；
- 责任模块；
- expected、actual、checks、score 等定位证据；
- 原始报告来源。

相同 Case 的相同失败会去重。当前可归因模块包括 Intent、Clarification、Planning、Rewrite、Retrieval、Coverage、Tool、Citation、Claim、PDF Grounding、Answer 和 Memory。

### 2.2 Strategy Candidate Generator

候选生成器只从代码 Allowlist 中提出以下变化：

- Prompt；
- Few-shot 示例；
- Policy 阈值；
- Retrieval 参数；
- Routing 规则。

候选包含目标模块、配置 Patch、依据 Case、风险等级和原因。所有候选固定：

```text
requires_human_approval = true
auto_apply = false
```

它不会编辑 Python 源码，不会修改认证、工具权限和部署配置。

### 2.3 Promotion Gate

Baseline 与 Candidate 必须使用完全相同的 `case_ids`。默认硬门槛：

| 门槛 | 默认值 | 作用 |
|---|---:|---|
| 最低总体质量提升 | 2 个百分点 | 防止无实质收益候选晋升 |
| 已通过 Case 回归 | 0 | 防止平均分掩盖局部负优化 |
| Critical Case 退化 | 0 | 保护关键能力 |
| Safety 退化 | 0 | 保护权限与安全边界 |
| Provider Failure 增量 | 0 | 防止把服务失败当能力提升 |
| 平均 Token 增幅 | ≤10% | 控制成本 |
| P95 延迟增幅 | ≤15% | 控制性能 |

全部通过时状态为 `eligible_for_human_approval`，不是 `promoted`；任何硬门槛失败都返回 `rejected` 和明确 blocker。

### 2.4 Version Registry

Registry 记录：

- Candidate Version；
- Gate 状态；
- 候选策略 ID；
- 对应报告路径；
- Rollback Version；
- 注册时间。

Registry 是 Append-only；重复版本不会覆盖历史。`active_version` 不会由进化流程自动改变，当前基线保持有效，直到人工审批和后续显式发布动作完成。

## 3. 一键运行

```powershell
Set-Location D:\langgraphproject
powershell -ExecutionPolicy Bypass -File .\scripts\run_evolution_cycle.ps1
```

默认运行冻结演示数据，0 LLM、0 外部工具调用，输出：

- `outputs/evolution/latest_evolution_report.json`
- `outputs/evolution/latest_evolution_failures.csv`
- `outputs/evolution/latest_evolution_candidates.csv`
- `outputs/evolution/strategy_versions.json`

CSV 可直接用 Excel 打开。

## 4. 使用真实评测报告

```powershell
D:\miniconda3\envs\paper_agent\python.exe -m eval_harness.evolution_cycle `
  --failures outputs\llm_core_eval\latest_llm_online.json `
  --scorecards outputs\evolution\real_scorecards.json `
  --output-dir outputs\evolution\real_run `
  --registry outputs\evolution\strategy_versions.json
```

Scorecard 格式：

```json
{
  "baseline": {
    "version": "prompt-v1",
    "case_ids": ["case-1", "case-2"],
    "pass_rate_pct": 50.0,
    "critical_pass_rate_pct": 100.0,
    "safety_pass_rate_pct": 100.0,
    "provider_failure_count": 0,
    "average_tokens": 4000,
    "p95_latency_seconds": 20.0,
    "per_case_passed": {"case-1": true, "case-2": false}
  },
  "candidate": {
    "version": "prompt-v2-candidate",
    "case_ids": ["case-1", "case-2"],
    "pass_rate_pct": 100.0,
    "critical_pass_rate_pct": 100.0,
    "safety_pass_rate_pct": 100.0,
    "provider_failure_count": 0,
    "average_tokens": 4200,
    "p95_latency_seconds": 21.0,
    "per_case_passed": {"case-1": true, "case-2": true}
  }
}
```

必须先真实运行 Candidate 版本并生成 Scorecard。内置 `evolution_scorecards_v1.json` 只是演示门控计算，不能作为项目真实提升数据。

## 5. 本轮演示结果

| 指标 | 结果 |
|---|---:|
| 输入失败记录 | 8 |
| 生成受限候选 | 5 |
| Gate | 通过 |
| 状态 | eligible_for_human_approval |
| 自动应用 | false |
| LLM 调用 | 0 |
| 定向测试 | 9/9 通过 |

这只证明闭环实现正确，不表示生产策略质量真实提升了 40 个百分点。

## 6. 安全边界

允许自动完成：失败抽取、归因、候选建议、指标比较、Gate 判定、版本登记。  
禁止自动完成：修改源代码、修改认证、扩大工具权限、写生产 `.env`、切换 active version、提交 Git、部署上线。

即使 Gate 全部通过，系统也只产生“可供人工审批”的候选。

## 7. 与现有 PaperAgent 的结合

- `trace_id` 提供失败请求关联。
- `failure_types` 来自 Clarification、Coverage、Citation、Claim、Grounding 和 Answer Verifier。
- 现有 422 项回归和 30 题 LLM 核心集可生成 Scorecard。
- Prompt A/B、RAG 参数评测和 Tool Router 指标可成为 Candidate 实验。
- Token、延迟和 Provider Failure 直接进入 Promotion Gate。
- Strategy Registry 为候选版本和回滚基线提供审计记录。

## 8. 后续扩展边界

v1 不继续扩大为自动训练平台。真正有数据后，可按优先级增加：

1. 将实际 Trace 自动导出为统一 Failure Record。
2. 为候选配置增加独立运行器，而不是手工准备 Scorecard。
3. 增加按任务类别分组的最低指标，防止总体平均掩盖小类退化。
4. 增加人工审批 API 和显式 Activate/Rollback 命令。

在这些能力完成前，不应把 `eligible_for_human_approval` 描述为已经自动上线。

## 9. 首次真实在线结果

已使用当前主模型对 Research Analyzer 的 zero-shot 与 few-shot 运行 6 题、12 次真实调用。few-shot 通过率由 16.67% 提升至 66.67%，但发生 1 个逐题回归且平均 Token 增加 28.92%，Promotion Gate 返回 `rejected`，未切换当前策略。详见 [真实在线测试报告](REAL_EVOLUTION_TEST_REPORT.md)。

随后测试最小 Schema Guard 候选：解析率由 50% 提升至 100%，没有逐题回归，P95 延迟下降 25.76%；但能力通过率保持 16.67%、平均 Token 增加 11.98%，仍被 Gate 拒绝。详见 [Schema Guard 真实测试](SCHEMA_GUARD_EVOLUTION_REPORT.md)。
