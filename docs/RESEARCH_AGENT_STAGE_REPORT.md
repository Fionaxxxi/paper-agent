# PaperAgent 研究型 Agent 阶段能力报告

## 1. 阶段目标

本阶段把 PaperAgent 从“论文检索后生成答案”升级为具有任务分级、结构化研究规划、有界执行、请求级证据管理、研究报告生成、逐引用验证和低成本失败修复能力的研究型 Agent。

当前核心路径：

```text
用户问题
→ Clarification Gate
→ Research Analyzer（L1/L2/L3）
→ Research Brief / Research Plan / Plan Validator
→ Research Scheduler
→ 多来源检索
→ Evidence Store
→ Evidence Coverage Gate
→ Research Writer
→ Citation Validator
→ Citation Repair
→ Answer Verify
→ Metrics
```

## 2. 已完成能力

### 2.1 澄清与上下文恢复

- 零 LLM 检测“它、这个方法、该论文”等中文指代；
- 唯一候选自动恢复，多候选或无候选主动询问；
- pending query 保存到 SQLite，会话下一轮可恢复；
- 澄清失败时在 Research Analyzer 和检索之前停止，避免错误扩散和 Token 浪费。

### 2.2 结构化研究分析

- L1 简单检索、L2 比较任务、L3 研究报告三级路由；
- L3 可使用一次结构化 LLM 分析目标、评价维度、Skill 与报告要求；
- Pydantic 校验 Research Analysis、Brief、Plan 和科研 Skill 输出契约；
- Policy Gate 保留时间、趋势、代表论文和研究空白等用户约束；
- 最多 5 个任务、最大并行数 2、最大 Replan 1 次。

### 2.3 有界 Research Scheduler

- 按 `depends_on` 编译拓扑执行波次；
- 未知依赖、循环依赖返回 `blocked_dependencies`；
- 综合任务只能排在依赖检索任务之后；
- L1/L2 不启用 Scheduler，保持快速路径。

### 2.4 Evidence Store 与 Coverage Gate

- 为论文生成稳定 Evidence ID；
- 按来源和定位符去重；
- 保留标题、来源、DOI、URL、页码、Chunk、摘要片段和关联任务；
- 建立 Task–Evidence 与 Claim–Evidence 输入；
- Coverage Gate 输出 `passed / partial / blocked / not_applicable`；
- 零覆盖时跳过 LLM，部分覆盖时要求 Writer 明确披露证据不足。

### 2.5 Research Writer 与科研 Skill

- Literature Review Skill；
- Paper Critique Skill；
- 强制区分论文事实、综合判断和证据不足；
- 重要事实使用 `[Evidence ID]`；
- 报告末尾输出证据索引；
- Paper Critique 明确“输入材料没有提供”不等于“论文没有进行”。

### 2.6 Citation Validator 与零 LLM 修复

Citation Validator 检查：

- Evidence ID 是否真实存在；
- 是否存在虚构引用；
- 综合判断是否在同一行附有效 Evidence ID；
- 是否存在证据索引；
- 批判报告是否把材料缺失过度推断成论文缺陷。

Citation Repair 只在以下条件下自动运行：

```text
唯一失败是 uncited_synthesis_claim
→ 漏引行明确出现论文标题
→ 标题可唯一映射到 Evidence Store
→ 在行末补全对应 Evidence ID
→ 重新运行 Citation Validator
```

无法唯一匹配、存在同名歧义或同时包含其他引用错误时不修改答案，也不猜测证据。

## 3. 正式评测结果

### 3.1 30 题在线 LLM 核心能力集

```text
案例数：30
通过数：29
通过率：96.67%
真实 LLM 调用：17
Token：62,525
耗时：435.097 秒
Provider 失败：0（正式基线）
```

唯一能力失败为 L3 时间趋势约束在结构化解析回退时保留不足；代码已经修复，定向复测遇到 Provider 连接失败，因此正式历史基线仍保留 29/30，不用外部服务失败覆盖原结论。

### 3.2 Research Writer v1

```text
案例数：4
自动通过率：75%
引用存在率：100%
虚构引用：0
声明局部引用覆盖率：91.67%
人工证据支持度：75%（3.0/4）
Token：18,464
```

主要问题：Agent Loop 综合判断缺少相邻引用；Paper Critique 把单句材料不足过度推断为论文无法通过严格审查。

### 3.3 Research Writer v2

```text
案例数：4
Provider 成功：4/4
自动通过率：75%
Citation Validator 通过：3/4
引用存在率：100%
虚构引用：0
声明局部引用覆盖率：91.67%
人工证据支持度：81.25%（3.25/4）
Token：18,061
```

Paper Critique 人工评分由 2/4 提升到 3/4，已经明确区分材料局限和论文缺陷。唯一剩余失败为 Agent Loop 综合比较缺少相邻 Evidence ID。

### 3.4 零 LLM Citation Repair A/B

```text
复用已有 v2 原文：是
修复案例：1
自动通过：3/4 → 4/4
Citation Validator：3/4 → 4/4
其他报告改动：0
新增 LLM 调用：0
Token 增量：0
```

## 4. 测试与复现

完整离线测试：

```powershell
D:\miniconda3\envs\paper_agent\python.exe -m pytest -q
```

最近完整结果：

```text
313 passed
148.53 秒
```

30 题真实 LLM 能力集：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_llm_online_eval.ps1
```

4 题 Research Writer 真实集：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_research_report_eval.ps1 --confirm-online
```

复用已有报告运行零 Token Citation Repair A/B：

```powershell
D:\miniconda3\envs\paper_agent\python.exe -m eval_harness.citation_repair_ab `
  --report outputs\research_report_eval_v2\latest_research_report_eval.json `
  --output outputs\research_report_eval_v2\citation_repair_ab.json
```

## 5. 当前边界

- Scheduler 已编译依赖波次，但实际串并行仍由 Retrieval Executor 控制；
- Task–Evidence 绑定 v1 使用词项重合启发式；
- Citation Validator 验证引用身份和局部覆盖，不等同于完整自然语言推理蕴含判断；
- Citation Repair 只处理标题可唯一匹配的漏引，不处理证据语义冲突；
- 本地 RAG、Dense、Hybrid、GraphRAG 与 LightRAG 仍由统一 Harness 评测后选择，不写死技术路线；
- Writer Reflection 暂不默认启用，只有确定性修复无法处理且证据充分时才值得建立 A/B。

## 6. 下一阶段建议

当前证据闭环已经适合作为简历项目展示。下一阶段不应继续扩大细粒度评测，而应优先：

1. 整理 API 演示入口和代表性请求；
2. 补充前端或最小可视化执行轨迹；
3. 接入 Zotero MCP 与 GitHub MCP；
4. 根据演示需求决定 Docker 和 CI；
5. 收集真实失败案例后，再决定是否开发受限 Writer Reflection。
