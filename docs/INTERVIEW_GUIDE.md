# PaperAgent 面试与演示指南

本文件用于三分钟快速讲解；逐题技术回答见 [PaperAgent 项目面试题完整回答](PROJECT_INTERVIEW_QA.md)。

更新日期：2026-08-23

## 1. 简历项目描述

PaperAgent｜基于 LangGraph 的证据驱动科研 Research Agent

- 设计 L0-L3 分层研究工作流，将意图识别、澄清、查询规划、多源检索、证据覆盖检查、答案生成和验证编排为可观测状态图；简单问候本地短路，复杂任务进入有界 Plan-and-Execute。
- 构建统一 Tool/MCP 治理层，接入 arXiv、OpenAlex、Crossref、Semantic Scholar、GitHub 与 Zotero，统一处理参数校验、权限、超时、重试和审计。
- 实现 Personal/Online/Hybrid 三类检索范围，以及 BM25、Dense、RRF 和置信度门控 Local RAG；支持个人论文库的用户级数据隔离。
- 建立 Evidence Store 与 Coverage、Citation、Claim、Grounding、Answer Verification 质量闸门，并通过有限 Replan/Reflection 做失败恢复，避免无界 Agent Loop。
- 支持 PDF 自动关键页选择与图、表、曲线、公式视觉理解，研究结论可导出中文 Word/PDF；提供 FastAPI Web 演示台、Docker、CI 和 422 项离线回归测试。
- 构建受控策略进化 Harness，将失败 Trace 转成 Badcase 与受限策略候选，通过质量、安全、成本、延迟和逐题无回归门控后只进入人工审批，禁止自动改代码或上线。

## 2. 三分钟讲解稿

### 0:00—0:30：项目解决什么问题

PaperAgent 解决的不是“让大模型概括一篇论文”，而是“怎样把一个开放研究问题变成有证据、可验证、成本受控的研究结论”。因此我把重点放在 Agent Engineering：任务理解、计划、工具执行、证据管理、质量验证和失败恢复都需要显式建模。

### 0:30—1:20：核心架构

系统入口是 FastAPI，核心由 LangGraph 管理共享状态和条件路由。简单问候直接本地返回，研究问题先经过澄清和复杂度分析，再形成查询计划。检索范围可以是在线论文、个人论文库或两者混合。所有外部调用统一经过 Tool Router、Registry、Policy 和 Executor，因此参数、权限、超时、重试与错误结构是统一的。

检索结果不会直接交给模型。它们先进入 Evidence Store，经过合并、去重、覆盖度检查和重排。复杂任务再通过 Planner、Executor、Reviewer 三段受限协作完成，但不会为了“多 Agent”额外制造无意义模型调用。

### 1:20—2:10：项目最有区别的能力

第一，系统不仅返回答案，还会公开 Evidence ID、检索来源、执行轨迹、Token 和节点耗时。第二，答案要经过 Citation、逐声明 Claim-Evidence、PDF Grounding 和最终 Answer Verification；证据不足时会安全降级，最多进行一次有依据的 Replan 或 Reflection。第三，PDF 不只提取文字，还会根据图表意图自动选择最多三页，使用视觉模型解析图、表、曲线和公式，再由主模型综合。

此外，系统有个人论文库和长期研究记忆。论文库存原始材料，长期记忆只保存验证通过、达到价值阈值且不冲突的派生研究结论，两者职责分离。

### 2:10—3:00：工程结果与取舍

项目提供网页、API、命令行、Docker 和 GitHub Actions。当前离线回归套件为 422 项全部通过；正式 LLM 核心评测集为 30 题，当前落盘结果为 29 题通过、通过率 96.67%，没有供应商失败。16 题最终回答 A/B 中，不含引用因素的内容质量分由 68.44 提升至 92.34，证据不足披露率由 28.57% 提升至 100%。PDF 视觉链路也使用真实 GraphRAG 论文页面完成过在线冒烟。

我刻意没有做无界 Agent Loop，也没有把 GraphRAG 或 LightRAG 写死为唯一方案。原因是简历项目更需要完整、可解释、可复现的闭环；复杂 RAG 方案应放入统一评测后再根据准确率、延迟、成本和维护难度选择。

## 3. 建议现场演示顺序

1. 打开首页，说明个人论文库、在线研究和 Hybrid 三种范围。
2. 点击“查看研究示例”，强调这是零 API 的稳定演示轨迹。
3. 展示 Research Plan、并行执行波次和 Planner → Executor → Reviewer。
4. 展示 Evidence Store 与 Coverage、Citation、Claim Support、Repair。
5. 展示最终结论及 Word/PDF 下载。
6. 点击“查看 PDF 示例”，展示自动选页、视觉任务、结构化契约和 Grounding。
7. 最后打开测试结果，说明离线回归和在线能力评测各自解决什么问题。

## 4. 常见追问

### 为什么使用 LangGraph？

因为流程存在多个条件分支、共享状态、失败恢复和审计要求。LangGraph 让这些决策成为显式节点和边，而不是隐藏在一个超长 Prompt 或循环中。

### 为什么需要 MCP？

项目内部工具层负责执行治理；MCP 提供标准化工具边界，使同一 GitHub、Zotero 等能力能被不同 Agent 或外部客户端复用。多 Agent 并不强制依赖 MCP，但 MCP 降低了重复适配成本。

### 为什么不是所有任务都调用大模型？

问候、明确指代、部分复杂度特征、工具权限和记忆写入最终决策都能由规则完成。这样可以降低 Token、延迟与不可预测性；只有语义判断真正有价值时才调用模型。

### 为什么不做无限 ReAct/Reflexion？

无界循环会放大成本和错误。项目只在可恢复、证据明确不足时允许有限 Replan 或 Reflection，并记录触发原因与次数。

### GraphRAG 和 LightRAG 怎么选？

论文研究可能受益于实体关系和跨文档结构，但并不意味着 GraphRAG 永远更优。项目保留统一评测接口，后续用研究问答正确率、证据覆盖、索引成本、查询延迟和更新难度决定，而不是预先写死。

## 5. 演示前检查

```powershell
Set-Location D:\langgraphproject
D:\miniconda3\envs\paper_agent\python.exe -m uvicorn app.api:app --host 127.0.0.1 --port 8000
```

浏览器打开 `http://127.0.0.1:8000/`，先使用两个零 API 示例；只有需要展示真实在线链路时才配置百炼和论文源凭据。
