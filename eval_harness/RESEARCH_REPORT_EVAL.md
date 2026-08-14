# 研究报告端到端评测

首版冻结 4 个代表案例，覆盖 Agent Loop 综述、RAG/GraphRAG 比较、单论文批判和反思记忆分析。人工标注位于 `datasets/research_report_v1.json`：每项关键声明都指定允许支持它的 Evidence ID。

自动指标：

- 引用存在率：输出引用中，能在该案例 Evidence Store 找到的比例；
- 虚构引用数：输出引用但 Evidence Store 不存在的 ID 数；
- 声明引用覆盖率：包含人工关键词的段落附近，是否出现人工允许的 Evidence ID；
- 结构完整率：要求的中文报告章节是否出现；
- LLM 调用数与 Token：只在在线模式计入。

离线验证评测器，不调用模型：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_research_report_eval.ps1
```

真实模型基线，会调用 4 次左右模型并产生 Token：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_research_report_eval.ps1 --confirm-online
```

输出位于 `outputs/research_report_eval/`，包含 JSON 全量结果和可直接用 Excel 打开的 CSV 表格。`reference_harness_validation` 的 100% 只证明人工参考报告和判分器一致，不是模型成绩；只有 `online_llm` 才是模型基线。
