# 在线 LLM 能力测试

这套测试与离线单元测试分离，会调用 `.env` 中配置的真实百炼兼容模型并产生 API 用量。默认正式核心集冻结在 `eval_harness/datasets/llm_core_v1.json`，包含 18 个任务分析案例、4 个查询规划案例和 8 个科研生成案例，共 30 题。原 7 题集保留为最低成本冒烟集。

## 一键运行

在项目根目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_llm_online_eval.ps1
```

只运行原 7 题冒烟集：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_llm_online_eval.ps1 `
  --dataset eval_harness/datasets/llm_online_v1.json `
  --output-dir outputs/llm_smoke_eval
```

运行前必须在 `.env` 配置 `OPENAI_API_KEY`，并保持 `RESEARCH_ANALYSIS_WITH_LLM=true`。脚本显式传入 `--confirm-online`，避免普通 pytest 或离线 Benchmark 意外产生费用。

只运行一个案例：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_llm_online_eval.ps1 --case generation_literature_review
```

如果模型已经运行并生成 JSON，但 CSV 或 Excel 报告阶段失败，可直接恢复报告，
不会再次调用模型：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_llm_online_eval.ps1 --report-only
```

修复代码后只重跑指定失败案例，并合并回现有完整报告：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_llm_online_eval.ps1 `
  --case analysis_l1_single_search `
  --case analysis_l3_research_program `
  --merge-existing
```

从某个时间戳 JSON 恢复 latest（不调用模型）：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_llm_online_eval.ps1 `
  --restore-report outputs/llm_core_eval/llm_online_YYYYMMDD_HHMMSS.json
```

## 输出

- `outputs/llm_core_eval/latest_llm_online.json`：完整机器可读报告与模型原始输出；
- `outputs/llm_core_eval/latest_llm_online.csv`：Excel 可直接打开的用例明细；
- `outputs/llm_core_eval/latest_llm_online.xlsx`：概览、用例明细和模型原始输出工作簿。

## 判定规则

- L1 简单检索和 L2 明确比较不得产生额外研究分析 LLM 调用；
- L3 复杂任务必须恰好完成一次结构化分析，等级、主 Skill 和 Plan Validation 正确；
- 生成案例必须命中预期 Skill、完成一次成功调用、达到最小完整度；
- 答案必须覆盖预先声明的语义要点并提及冻结证据中的论文身份；
- API 失败、回退回答、缺少关键结构或超出调用预算均判定失败。

这些是可重复的自动验收门槛，不替代人工学术质量评审。Excel 的“模型原始输出”工作表用于逐条人工 Review。
