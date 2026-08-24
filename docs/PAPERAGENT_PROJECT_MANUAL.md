# PaperAgent 项目完整说明书

> 文档定位：PaperAgent 唯一总说明（Single Source of Truth）  
> 更新日期：2026-08-22  
> 项目状态：简历展示版，核心链路完成，后续以产品化和有数据依据的优化为主  
> 目标读者：项目作者、面试官、代码评审者、后续维护者

## 0. 如何阅读这份文档

这份文档集中说明 PaperAgent 的项目目标、完整架构、执行流程、每层设计、每个核心模块、数据与状态、测试结果、性能数据、开发迭代记录和未来扩展方向。以后项目现状以本文件为准；其他文档保留为专项实现细节或历史实验凭证。

建议阅读顺序：

```text
第一次了解项目
→ 阅读第 1～4 章：定位、特色、架构和执行流程
→ 阅读第 5～12 章：各层和模块设计
→ 阅读第 13～15 章：测试、性能和安全边界
→ 阅读第 16～18 章：迭代记录、未来扩展和运行方式
```

文档中的状态含义：

| 状态 | 含义 |
|---|---|
| 已完成 | 已有代码实现，并至少经过离线回归或真实冒烟验证 |
| MVP | 主路径可用，但规模、权限或运维能力仍适合个人项目环境 |
| 候选 | 尚未写死技术选型，必须通过统一评测后才决定是否引入 |
| 暂缓 | 对当前简历项目收益不足，避免为了技术堆叠增加复杂度 |

---

## 1. 项目概述

### 1.1 一句话介绍

PaperAgent 是一个基于 LangGraph 的证据驱动科研论文 Agent：它把自然语言问题转换成受控研究计划，从在线论文源、个人论文库、本地全文和 PDF 图表中收集证据，经过覆盖度、引用、声明和答案验证后输出可追溯的中文结论，并支持会话记忆、长期研究记忆和 Word/PDF 报告导出。

### 1.2 项目解决的问题

普通“论文问答”通常只有一条链路：问题 → 搜索 → 将结果交给 LLM → 输出答案。它容易遇到：

- 简单问候也调用模型，浪费 Token；
- 复杂研究问题没有拆解，检索覆盖不完整；
- 数据源、工具权限、超时和错误缺少统一治理；
- 检索结果虽然很多，但不能说明每个结论由什么证据支持；
- 低质量结果无限重试，形成昂贵的 Agent Loop；
- PDF 只提取文本，无法理解架构图、表格、曲线和公式；
- 所有对话都写入记忆，造成污染、重复和过期信息；
- Prompt 修改只看平均分，可能修好一类问题却让已有能力退化。

PaperAgent 将这些问题拆成可观察、可测试的工程节点，以代码 Policy 约束 LLM 的自由度。

### 1.3 设计原则

1. **证据优先**：生成结论前先形成 Evidence Store，生成后再验证 Claim 与 Evidence。
2. **成本受控**：规则能可靠处理的 Smalltalk、明确指代和部分路由不调用 LLM。
3. **有限自治**：允许 Planning、Replan 和 Reflection，但循环次数有硬上限。
4. **工作流优先**：主链路采用固定 Workflow；只在复杂 L3 任务中启用有界角色协作。
5. **工具统一治理**：工具先注册、再路由、再过权限 Policy，最后由 Executor 执行。
6. **按需记忆**：不是每轮都召回、也不是每个回答都长期保存。
7. **评测决定升级**：RAG、Prompt、路由和模型候选不凭感觉替换，必须通过冻结集和晋升门。
8. **工程事实透明**：已实现、MVP、候选和暂缓能力严格区分。

### 1.4 当前完成度

| 能力域 | 状态 | 当前实现 |
|---|---|---|
| LangGraph 主工作流 | 已完成 | 条件边、共享 State、Checkpoint、停止原因和节点指标 |
| 多源论文检索 | 已完成 | arXiv、OpenAlex、Crossref、Semantic Scholar |
| Tool/MCP 治理 | 已完成 | Router、Registry、Policy、Executor、统一契约与错误 |
| 本地全文 RAG | 已完成 | PDF Chunk、BM25、MPNet Dense、RRF、置信度门控 Hybrid |
| 在线论文全文研究 | 已完成 | 深度任务自动获取可信开放 PDF、项目内缓存、分页分块、按问题召回并保留页码 |
| 宽泛领域探索 | 已完成 | 科研缩写规范化、L2 概览路由、差异化子查询和 arXiv/OpenAlex 多源检索 |
| Harness 工程研究 | 已完成 | Harness/Scaffolding/Runtime 术语映射、Workflow 关系检索、核心概念覆盖门与定向 Replan |
| 查询缓存语义门 | 已完成 | 来源隔离缓存、核心概念验证、不合格缓存穿透在线源、拒绝错误缓存锁定 |
| Research Agent | 已完成 | L1/L2/L3 分级、Brief、Plan、Schedule、Evidence、Coverage |
| 幻觉抑制 | 已完成 v1 | Retrieval Gate、Citation、Claim-Evidence、PDF Grounding、Answer Verify |
| 有限 Agent Loop | 已完成 | Retrieval Replan ≤1、Answer Reflection ≤1 |
| 记忆系统 | 已完成 v1 | SQLite 会话/Checkpoint、Long-Term Memory RAG、Write Gate |
| 个人论文库 | MVP | 注册登录、Owner 隔离、上传/删除、Personal/Online/Hybrid |
| PDF 多模态 | 已完成 v2 | 自动关键页、Figure/Table/Chart/Formula、OCR + 主模型综合 |
| 报告导出 | 已完成 v1 | 已生成结论导出 Word/PDF，不增加 LLM 调用 |
| Web、Docker、CI | 基础版完成 | 研究控制台、Swagger、容器、健康检查、GitHub Actions |
| 受控策略进化 | 已完成 v1 | Badcase → Candidate → Scorecard → Promotion Gate → Registry |

---

## 2. 项目特色与简历价值

### 2.1 Graph Engineering，而不是单次 Prompt

核心特色是把科研研究过程建模为可验证的状态图。每个节点只负责一类决策，节点之间通过类型化 State 交接，因此可以看到“为什么走这条路径、在哪一步失败、是否发生重试、花了多少 Token”。

### 2.2 私人知识与公开知识结合

系统支持三种检索范围：

```text
Personal：只检索当前用户论文库
Online：只检索公开论文数据源
Hybrid：个人库与在线源有界并行 → 统一证据层
```

这使项目从“arXiv 搜索 Demo”升级为可以结合用户已有材料与新论文开展研究的产品原型。

### 2.3 证据驱动与分层幻觉抑制

PaperAgent 不依赖一句“不要幻觉”的 Prompt，而是采用多层防线：

```text
检索质量门控
→ Evidence Coverage
→ 基于 Evidence ID 生成
→ Citation Validator
→ Claim-Evidence Validator
→ PDF Grounding Validator
→ Answer Verifier
→ 有修复依据时才 Reflection
```

### 2.4 有界 Agent Loop

复杂任务可以 Replan 和 Reflection，但不是无限 ReAct：检索恢复最多一次，答案反思最多一次，且必须存在明确失败类型或可修复证据。这样保留 Agent 的恢复能力，同时限制路径震荡、延迟和 Token。

### 2.5 会读图表的论文 Agent

系统先在本地识别视觉意图和关键页，再将最多 3 页发送给 `qwen3.5-ocr`，输出结构化视觉证据，最后由主模型结合 PDF 文本综合。针对架构图、表格、曲线和公式分别选择 Skill，而不是只做全文 OCR。

### 2.6 受控自进化，而不是自动改代码

Eval 和 Trace 中的 Badcase 会形成结构化 Failure Dataset。系统只从 Allowlist 中提出 Prompt、Policy、Routing 或 RAG 候选，再用相同冻结集比较质量、逐题回归、安全、Token 和 P95 延迟。候选最多进入人工审批，不能自行修改代码、切换生产版本或部署。

---

## 3. 完整架构示意图

### 3.1 运行时主架构

```text
用户
├─ Web Research Console
├─ FastAPI / Swagger
└─ CLI
   ↓
PaperAgentService
├─ Trace ID
├─ User / Session / Conversation 身份
├─ PDF 输入与安全校验
├─ 会话上下文 / Checkpoint 恢复
└─ AgentState 初始化
   ↓
LangGraph 主工作流
├─ Intent Router
│  ├─ Smalltalk → 本地零 LLM 回答 → 结束
│  └─ 论文任务 → 继续
├─ Clarification Resolver
│  ├─ 明确指代 → 规则恢复
│  ├─ 描述性指代 → 受限语义解析
│  └─ 证据不足 → 主动询问 → 等待用户
├─ Research Analyzer
│  ├─ L1：单一检索 / 简单问答
│  ├─ L2：比较 / 组合任务
│  └─ L3：多维复杂研究任务
├─ Memory Retrieval Gate
│  └─ 仅显式历史请求或 L3 → Owner-scoped Top-K Memory RAG
├─ Query Rewrite → Query Plan → Plan Validator → Scheduler
│  ├─ 子查询与依赖
│  ├─ 可并行执行波次
│  ├─ 最大并发限制
│  └─ 非法或过大计划阻断
├─ Retrieval Router
│  ├─ Online
│  │  └─ Tool Router → Registry → Policy → Executor
│  │     ├─ arXiv
│  │     ├─ OpenAlex
│  │     ├─ Crossref
│  │     └─ Semantic Scholar
│  ├─ Personal Library
│  │  └─ Owner-scoped PDF Chunk → BM25 / Local RAG
│  ├─ Hybrid
│  │  └─ Personal + Online 有界并行
│  └─ PDF Reading
│     ├─ pypdf 全文和页码
│     └─ 关键页 → qwen3.5-ocr → 结构化视觉证据
├─ Result Merge / Metadata Normalize / Repository Enrichment
├─ Evidence Store
│  ├─ 类型化证据与 Evidence ID
│  ├─ 来源、DOI、URL、页码定位
│  ├─ 去重、污染过滤和规范化
│  └─ Task ↔ Evidence 映射
├─ Coverage / Retrieval Quality Gate
│  ├─ 通过 → 继续
│  ├─ 可恢复 → Retrieval Replan（最多 1 次）
│  └─ 仍不足 → 明确降级或停止
├─ Reason / Skill Router
│  ├─ QA / Summary / Compare / Citation
│  ├─ Literature Review / Paper Critique / Research Direction
│  └─ PDF / Figure / Table / Chart / Formula
├─ Generate / Research Writer
├─ Verification Pipeline
│  ├─ Citation Validator / Citation Repair
│  ├─ Claim-Evidence Validator
│  ├─ PDF Grounding Validator
│  └─ Answer Verifier
├─ Answer Reflection（最多 1 次，必须有修复证据）
├─ Memory Write Gate
│  ├─ Verification 前置条件
│  ├─ Value / Stability / Time-sensitive Policy
│  ├─ Dedup / Conflict / Expiry
│  └─ Write / Merge / Update / Skip
├─ L3 Multi-Agent Trace
│  └─ Planner → Executor → Reviewer（角色交接，不增加自由循环）
└─ Metrics / Tool Audit / Token / Latency / Stop Reason
   ↓
输出
├─ 格式化中文研究回答
├─ 论文证据与引用
├─ LangGraph 执行轨迹
├─ Token / 延迟 / 工具调用记录
└─ 可下载 Word / PDF 研究报告
```

### 3.2 离线评测与受控进化旁路

```text
单元测试 / 在线评测 / 真实 Trace
→ 失败记录标准化
→ Failure Attribution
→ Failure Dataset
→ Allowlisted Candidate Generator
→ 相同冻结集运行 Baseline 与 Candidate
→ Scorecard
→ Promotion Gate
   ├─ 总体质量提升
   ├─ 逐题零回归
   ├─ Critical / Safety 零退化
   ├─ Provider Failure 不增加
   ├─ 平均 Token 增幅 ≤ 10%
   └─ P95 延迟增幅 ≤ 15%
→ Version Registry
   ├─ rejected：保留失败实验，不改变当前策略
   └─ eligible_for_human_approval：等待人工审批，绝不自动上线
```

### 3.3 数据与存储架构

```text
SQLite
├─ 用户、Token 与个人论文元数据
├─ LangGraph Checkpoint / 会话状态
├─ Long-Term Research Memory
└─ Memory Conflict Audit

文件系统
├─ data/papers：本地论文 PDF
├─ data/cache：Embedding、索引和 PDF 页面缓存
├─ logs：结构化运行日志
├─ outputs：评测 JSON / CSV / XLSX 和真实冒烟结果
└─ docs：总说明与专项实验报告

外部服务
├─ 百炼兼容 OpenAI API：主模型与 OCR 模型
├─ arXiv / OpenAlex / Crossref / Semantic Scholar
└─ 可选 Zotero / GitHub MCP Client
```

---

## 4. 一次请求的完整执行流程

### 4.1 通用研究请求

```text
接收 query
→ 建立 trace_id、user_id、conversation_id
→ 加载最近会话和 Checkpoint
→ Intent 判断
→ 必要时恢复指代或主动澄清
→ 判定 L1/L2/L3、目标、维度、数据源要求和 Skill
→ 按需召回长期记忆
→ 查询清洗与改写
→ 生成并校验研究计划
→ Scheduler 计算依赖与并行波次
→ Retrieval Router 选择 Online / Personal / Hybrid / PDF
→ 工具层执行检索，或本地 RAG / PDF Reader 收集材料
→ 合并、去重、标准化为 Evidence Store
→ Coverage 与 Retrieval Quality 判断证据是否足够
→ 不足且可修复时最多 Replan 一次
→ Skill Router 选择回答策略
→ Writer 严格基于证据生成
→ Citation / Claim / Grounding / Answer 验证
→ 有明确修复项时最多 Reflection 一次
→ Memory Write Gate 决定是否沉淀研究结论
→ 保存 Checkpoint、Trace、指标
→ 返回答案、证据、轨迹和报告下载入口
```

### 4.2 五类典型路径

| 用户请求 | 实际路径 | 成本控制点 |
|---|---|---|
| `hi` | Intent Router → 本地 Smalltalk → 结束 | 0 LLM、0 检索 |
| “找 RAG 论文” | L1 → 单查询 → Online → QA/Summary → Verify | 通常不拆复杂计划 |
| “比较 GraphRAG 和 LightRAG” | L2 → 双方子查询 → 并行检索 → 双实体 Coverage → Compare | 缺一方证据时不强行比较 |
| “分析 Agent Memory 的方向、问题和趋势” | L3 → Analyzer → 多维 Plan → Scheduler → 多源证据 → Literature Review → 多层验证 | 只有复杂任务承担额外分析成本 |
| “解释 PDF 第 4 页架构图” | PDF 路由 → 页面文本 + 指定页 OCR → Figure Skill → Grounding | 页面最多 3 页；默认视觉关闭 |

---

## 5. 接入层与服务层设计

### 5.1 Web Research Console

网页是非技术用户的主要入口，支持研究问题、检索范围、个人论文库、PDF 页面分析、示例轨迹和报告导出。结果区展示正常排版后的 Markdown，而不是原始 Markdown 代码；同时展示 Evidence、Plan、节点耗时、工具和质量状态，突出 Agent 的可观察过程。

关键文件：`app/static/index.html`、`app/static/app.js`、`app/static/*.css`。

### 5.2 FastAPI / Swagger

FastAPI 定义 HTTP 接口和依赖注入；Pydantic 校验请求与响应结构；Uvicorn 提供 ASGI 运行服务。接口层只处理协议、身份和序列化，Agent 决策留在 Service 与 LangGraph，避免业务逻辑散落在 Controller。

关键文件：`app/api.py`、`app/schemas.py`。

### 5.3 CLI

CLI 用于本地快速调试和无前端演示，复用同一 Agent 服务，不维护第二套业务流程。关键文件：`main.py`。

### 5.4 PaperAgentService

Service 是 API/CLI 与 LangGraph 之间的应用层边界，负责：

- 生成和贯穿 `trace_id`；
- 解析用户、会话和 Conversation 身份；
- 校验 PDF 路径、页码与上传归属；
- 加载会话上下文与 Checkpoint；
- 初始化 AgentState 并调用 Graph；
- 整理最终响应和报告导出所需数据。

关键目录：`services/`。

---

## 6. LangGraph 编排层完整设计

### 6.1 为什么使用 LangGraph

项目不是为了“使用框架”而使用 LangGraph。它解决的是有状态、分支、恢复和审计问题：固定节点降低行为漂移；条件边明确何时结束、澄清、重试；统一 State 避免模块靠隐式 Prompt 传递信息；Checkpoint 支持多轮继续；节点级指标可以定位延迟和失败。

### 6.2 AgentState

State 包含请求身份、原问题、上下文、研究分析、改写查询、子任务计划、调度波次、论文结果、Evidence、覆盖度、质量状态、答案、引用/声明验证、重试计数、记忆决策、Token、节点耗时、工具审计和停止原因。State 是执行事实，不等同于全部 Prompt 上下文；只有当前节点需要的字段才会进入模型输入。

关键文件：`agent/state.py`。

### 6.3 Intent Router

先以确定性规则识别问候、感谢等低风险输入，本地生成固定自然语言回答。论文检索、总结、比较、PDF、引用和研究意图才进入主图。该设计直接解决“输入 hi 也走完整流程”的 Token 浪费。

关键文件：`agent/router.py`、相关 Node 与 `tests/test_intent_router.py`。

### 6.4 Clarification Resolver

处理三种情况：

1. 明确序号或“上一条”等可验证指代，用会话状态零 LLM 恢复；
2. “那篇关于记忆的论文”等描述性指代，只在有限候选中进行一次语义判断，并用置信度 Policy 约束；
3. 候选不存在、序号越界或语义置信度不足，主动询问用户，不猜测。

这使多轮补充能复用状态，同时防止错误指代污染后续计划。

### 6.5 Research Analyzer

Analyzer 输出结构化研究意图：任务等级、主题、目标、评估维度、来源要求、主/次 Skill、是否多源、是否需要报告、置信度和原因。明确简单请求由规则识别，复杂研究请求可调用主模型；Pydantic Contract 和后置 Policy 校验其格式和边界。

等级定义：

- L1：单目标、简单检索或事实型问答；
- L2：比较、组合、需要双方证据或有限拆分；
- L3：多维研究、趋势、开放问题、方法学评价或正式报告。

关键文件：`research/analyzer.py`、`research/contracts.py`。

### 6.6 Query Rewrite

Rewrite 负责清理会话口语、补回已确认实体、规范学术关键词、保留年份和限定词，并生成适合数据源的查询。它不是任意扩写：不能凭空增加研究对象，也不能改变用户范围。当前采用规则与受控模板，复杂语义升级必须经专项评测。

对于“梳理某主题的代表论文、方法比较和研究空白”这类 L3 请求，系统不会把中文任务描述原样提交给英文论文库，而是将同一研究主题拆成 `representative/survey`、`methods/evaluation`、`limitations/open problems` 等英文检索式。用户给出的“2023 年以来”等时间约束在检索后再次执行确定性年份过滤，避免供应商模糊召回突破用户范围。

### 6.7 Query Plan 与 Plan Validator

L1 通常只有一个任务；L2 比较拆成实体 A、实体 B 和综合任务；L3 根据 objectives 与 dimensions 形成有向无环依赖。Validator 检查任务 ID、依赖是否存在、是否成环、数量和深度是否超预算、查询是否为空，非法计划不会直接执行。

### 6.8 Scheduler

Scheduler 将 DAG 转成执行波次：同一波中无依赖的子查询可以异步并行；后续综合任务等待依赖完成。并发量有上限，输出顺序保持确定，避免并行造成结果随机覆盖。

关键文件：`research/planning.py`、`research/scheduler.py`。

### 6.9 Retrieval Replan

Coverage 或质量门控失败时，系统根据缺失实体、维度或来源构造一次定向补检，不重新规划全部任务。重试计数写入 State，超过 1 次必须停止或降级，避免路径震荡。

### 6.10 Answer Reflection

只有 Answer Verifier 给出可修复问题且已有证据足以修复时，才再次调用模型。Reflection 不能新增未检索事实，也不能无限自评；最多一次，修复前后都保留审计记录。

---

## 7. Tool 与 MCP 层设计

### 7.1 统一执行链

```text
Retrieval Task
→ Tool Router：根据数据源和任务选择工具名
→ Registry：查找实现和契约
→ Policy：检查是否启用、参数和权限
→ Executor：Pydantic 校验、超时、有限重试、错误归一化、指标
→ Adapter / MCP Client
→ 统一 Paper / ToolError 结果
```

### 7.2 各组件职责

| 组件 | 作用 | 防止的问题 |
|---|---|---|
| Tool Router | 选择能力，不直接执行业务代码 | 路由与实现耦合 |
| Registry | 名称到实现的集中映射 | 到处 `if/else`、重复初始化 |
| Policy | 白名单、参数、权限和开关 | 未授权调用、范围扩大 |
| Executor | 校验、超时、重试、审计、统一错误 | 工具异常击穿主图 |
| Adapter | 将各供应商响应转成统一 Paper 模型 | 下游绑定外部字段 |

### 7.3 MCP 的作用与当前边界

MCP 是工具发现与调用协议，不是“多 Agent 必须使用的框架”。PaperAgent 增加 MCP，是为了让同一工具可以被本项目、其他 Agent 或外部 MCP Host 通过统一契约复用，并隔离进程和实现细节。

当前包括：

- `paper.catalog.search.mcp`：项目自己实现的本地 Paper Catalog MCP Server，不是官方现成工具；
- Zotero MCP Client：访问用户文献库的可选集成；
- GitHub MCP Client：补充论文对应实现仓库的可选证据。

原始 Tool 是 Python 进程内调用，延迟低、调试简单；MCP Tool 经过协议边界，复用性和隔离更好，但有序列化和部署成本。因此内部核心链路不强制全部 MCP 化。

关键目录：`tools/`、`mcp_servers/`。

---

## 8. 检索、RAG 与证据层设计

### 8.1 在线数据源

| 数据源 | 当前职责 | 说明 |
|---|---|---|
| arXiv | 预印本发现与摘要 | 无 API Key；进行 withdrawn 等卫生过滤 |
| OpenAlex | 跨来源论文与引文元数据 | API Key 可选；`OPENALEX_MAILTO` 用于礼貌池联系信息 |
| Crossref | DOI 和规范出版元数据校验 | 不把模糊命中直接当权威身份 |
| Semantic Scholar | 论文、引用和影响信息补充 | 按配置启用并统一限流/错误 |

### 8.2 Local RAG

```text
PDF
→ 文本抽取和页码保留
→ Chunk
→ BM25 词法索引
→ multilingual MPNet Dense Embedding
→ 查询时 Dense 召回
   ├─ Top-1 和分数间隔达到门槛 → 使用 Dense
   └─ 置信度不足 → 复用 Dense 排名 + BM25 → RRF 融合
→ Top-K Chunk + document_id/page/source
```

Dense 适合语义改写和同义表达，BM25 适合专有名词、公式名和精确关键词。RRF 以排名而非不可比的原始分数融合两路结果。当前主要配置为 MPNet Dense、RRF 常数 40、候选池 50；最终参数以配置文件和评测结果为准。

### 8.3 为什么当前不是 GraphRAG 或 LightRAG

当前 Local RAG 是 BM25 + Dense + RRF 的混合检索，没有构建实体关系图、社区摘要或 LightRAG 双层图索引，因此不能称为 GraphRAG/LightRAG。LangGraph 负责 Agent 工作流编排，不等于图知识库。

GraphRAG 对跨论文实体关系、研究脉络和全局主题总结有潜力，但构建/更新成本高；LightRAG 更轻，但是否适合本项目不能凭名称判断。两者作为候选，未来用同一学术任务集比较召回、Faithfulness、延迟、成本和更新难度后再选型。

### 8.4 Evidence Store

所有来源先转成统一证据对象，包含 Evidence ID、论文身份、标题、作者、年份、摘要或 Chunk、URL/DOI、页码、来源类型、对应任务和检索分数。在线论文会统一生成可直接打开的 HTTPS 证据链接，前端分别提供“打开论文”和“查看 PDF”；DOI 转换为 `https://doi.org/...`，本地 Chunk 只显示页码与 Chunk ID。它是 Retrieval 与 Writer 之间的隔离层：Writer 只消费可定位证据，不直接处理供应商原始 JSON。

### 8.5 Coverage 与质量门控

Coverage 检查计划中的实体、维度、来源和子任务是否有证据映射；明确比较必须覆盖双方。检索质量结合数量、相关性、身份有效性和任务覆盖判断 `sufficient / retryable / insufficient`。L2/L3 的规则评估使用规范化英文主题词统计真实主题命中文献数，不再以中文整句是否出现在英文摘要中作为相关性依据；至少两篇主题证据才能越过生成门槛，一篇或全无关结果仍会阻断。Analyzer 声明需要多源时，Online 执行层会使用 arXiv 与 OpenAlex，而不是因界面选择 Online 就固定退化为单一 arXiv。不足时先定向补检；仍不足则明确告诉用户证据边界，而不是生成看似完整的结论。

关键目录：`local_rag/`、`retrieval/`、`research/evidence_store.py`、`research/coverage.py`。

---

## 9. Skill、生成与验证层设计

### 9.1 Skill Router

Skill 是带明确输入、证据要求和输出约束的回答策略，不是另一个任意自治 Agent。当前支持：

| Skill | 使用场景 |
|---|---|
| QA | 简单论文问答 |
| Paper Summary | 单篇或少量论文总结 |
| Paper Compare | 双方或多方法比较 |
| Citation | 引用和文献身份任务 |
| Literature Review | 多论文、多维研究综述 |
| Paper Critique | 方法、实验和局限性批判性分析 |
| Research Direction | 方向、机会和开放问题 |
| PDF Reading | PDF 文本阅读 |
| Figure Understanding | 架构图、流程图、示意图 |
| Table Analysis | 实验表、指标、消融 |
| Chart Analysis | 曲线、柱状、散点、热力图等 |
| Formula Explanation | 公式、符号和损失函数 |

简单规则可可靠命中时不调用模型；复杂研究意图复用 Analyzer 的 `primary_skill`，避免再为 Skill 选择增加一次 LLM。

每个 Skill 由四部分组成：

1. `name / description / need_llm`：声明能力身份与是否需要模型；
2. `build_prompt` 或规则 `run`：定义如何完成任务；
3. Context Policy：决定是否加载历史、长期记忆、论文、PDF 和元数据，并限制数量与字符；
4. 输出与验证契约：普通研究回答进入引用/声明验证，PDF 专项能力还具有 Pydantic Structured Output 和 Grounding。

Skill 不是把所有 Prompt 同时注入上下文。路由顺序为：L3 只接受 Research Analyzer 白名单中的研究 Skill；PDF 在用户指定或自动选页后按公式、图表、表格、架构图关键词选择一个专项 Skill；其余任务按 `task_type` 选择 Summary、Compare、Recommend、Citation 或 QA。最终只构造当前主 Skill 的 Prompt，避免 Skill 数量增加时上下文线性膨胀。

### 9.2 Generate / Research Writer

Writer 接收用户目标、研究计划、Evidence Store、Coverage、按需记忆和选定 Skill。Prompt 要求区分证据事实与推断、使用 Evidence ID、披露证据不足、禁止引用不存在的来源。L2/L3 同次生成内部 Memory Metadata，前端只展示清理后的正常答案。当前主模型强制启用思考，因此 Writer 使用 `GENERATE_THINKING_BUDGET=400` 限制隐藏推理，并用 `GENERATE_MAX_TOKENS=1800` 为可见报告保留有界预算，防止长篇生成超过上游连接持续时间或正文预算被隐藏思考耗尽；连接失败时返回明确的检索降级结果，不伪装成正式验证通过的研究结论。

### 9.3 Verification Pipeline

| 验证器 | 检查内容 | 失败后的处理 |
|---|---|---|
| Citation Validator | 引用格式、Evidence ID 和来源存在性 | 确定性修复或标记失败 |
| Citation Repair | 可由已有 Evidence 修复的引用 | 不新增来源、不猜 DOI |
| Claim-Evidence Validator | 每个声明与证据的 supported/partial/contradicted/insufficient | 降低支持率或触发有限修复 |
| PDF Grounding | 页码、视觉证据模式和 PDF 来源一致性 | 禁止使用未发送/未解析页面信息 |
| Answer Verifier | 目标覆盖、关键约束和整体可用性 | 有证据时最多 Reflection 一次 |

### 9.4 轻量 Multi-Agent

项目不是 Master + 大量自由 Sub-Agent 集群，而是固定 Workflow 为主、复杂 L3 任务增加 Planner、Executor、Reviewer 三个逻辑角色。角色通过同一 State 和明确交接对象协作，不靠自由聊天；现阶段复用已有节点，额外 LLM 调用为 0。这种设计更容易复现、测试和控制成本。

---

## 10. PDF 多模态设计

### 10.1 两阶段视觉路径

```text
用户问题
→ 识别 Figure / Table / Chart / Formula 意图
→ 显式页码优先；否则本地扫描图注和关键词选关键页
→ PyMuPDF 将最多 3 页渲染为 PNG
→ qwen3.5-ocr 提取布局、文字和目标视觉信息
→ Pydantic 结构化为 Visual Evidence
→ qwen3.7-max-2026-05-17 结合页面文本与 Visual Evidence 综合
→ PDF Grounding Validator
```

### 10.2 安全与成本边界

- 默认 `PDF_VISION_ENABLED=false`，图片不出站；
- 只有明确视觉意图或用户指定页码才触发；
- 一次最多 3 页，自动扫描上限 120 页；
- 不在日志保存 API Key、Base64 图片和本地绝对路径；
- OCR 不确定的刻度、颜色、上下标和连线必须显式标记，不能补猜；
- 当前只选页面，尚未裁剪单一图表区域或拼接跨页图表。

---

## 11. 上下文、会话与长期记忆

### 11.1 三类状态

| 类型 | 解决的问题 | 当前存储 |
|---|---|---|
| 运行 State | 当前一次 Graph 节点间传递事实 | 进程内 State + Checkpoint |
| 会话记忆 | 多轮补充、指代和最近上下文 | SQLite；兼容旧文件迁移路径 |
| 长期研究记忆 | 跨会话复用已验证研究结论 | SQLite Long-Term Memory |

### 11.2 会话压缩

#### 上下文如何逐轮增长

每次请求结束后，用户问题和助手回答作为独立消息追加到 SQLite。下一次请求按 `conversation_id` 读取消息；默认最近 6 条保持原文，更早消息进入确定性提取式摘要。这里的“6 条”是消息条数，不是 6 个完整问答轮次。

```text
第 1～3 个问答轮次
→ 最多 6 条 user/assistant 消息全部作为最近原文

继续对话
→ 最新 6 条仍保留原文
→ 更早消息按时间顺序组成提取式摘要
→ 再与研究主题、偏好、活跃论文一起按预算装配
```

#### 什么时候触发压缩

当前不是通过估算模型 Token 到达 80%/90% 才触发，也不是每轮额外调用摘要模型。只要消息数超过 `MEMORY_RECENT_MESSAGES=6`，构建上下文时就对更早消息进行零 LLM 压缩；摘要最大 `MEMORY_SUMMARY_MAX_CHARS=1200`，最终短期上下文最大 `MEMORY_CONTEXT_MAX_CHARS=2400`。

#### 保留什么、丢弃什么

Prompt 优先保留三类信息：结构化研究状态（用户偏好、当前主题、活跃论文）、旧消息摘要、最近消息原文。装配时分别获得有限预算，最近消息占比最高。旧摘要超过预算时保留靠后的内容，因为它通常距离当前任务更近。

被“丢弃”的是本次 Prompt 中的冗余文本，不是数据库原始消息。完整消息仍保存在 SQLite，可用于审计、重新构建上下文或隐私删除。因此“摘要后原文不再存在”的说法不准确。

#### 第 10 轮以后如何处理

第 11 轮不会把前 10 轮全部原样送进模型。系统重新读取该会话消息，把最新 6 条作为原文，把更早消息生成受限提取式摘要。当前实现不是持久化的增量语义摘要：每次从数据库中的早期原文重新构建摘要，所以模型 Token 有上限，但数据库读取和本地摘要成本仍会随历史增长。生产版本可增加摘要 Checkpoint、按消息游标增量合并和 Token-aware Budget。

#### 为什么不每轮使用 LLM 摘要

对当前单机简历项目，确定性压缩有 0 LLM、结果稳定、易回归的优点。代价是不能理解复杂语义优先级，可能截断较早但重要的约束。项目通过结构化 `user_preferences / active_topics / active_papers` 单独保留重要研究状态来降低风险；未来若引入小模型摘要，仍需保留用户硬约束、未完成任务、实体 ID、证据引用和最近原文，并通过回归集验证压缩后任务一致性。

### 11.3 Skill Context Policy：不是把 State 全部塞进 Prompt

AgentState 保存完整执行事实，但 `build_skill_context` 只按当前任务的 Context Policy 选择：

| 上下文部分 | 控制方式 | 当前优化 |
|---|---|---|
| 会话历史 | `use_history` + 2400 字符总预算 | 旧摘要 + 最近原文 |
| 长期记忆 | Need Detection + Top-K 3 + 3000 字符 | 仅显式历史/L3 按需召回 |
| 论文结果 | `max_documents` + 单文档截断 | 不注入供应商完整 JSON |
| PDF | `use_pdf` + 最大字符数 | 仅 PDF Skill 使用，视觉最多 3 页 |
| 元数据 | `use_metadata` | Trace 等结构化信息不混入正文 |

工具结果先规范化为 Paper/Evidence，只把 Top-K、片段和 Evidence ID 交给 Writer；原始大 JSON、缓存对象、全部 AgentState 和不相关 Skill 描述不会进入模型上下文。

### 11.4 Memory Retrieval Gate

长期记忆不是每轮注入。只有用户显式说“继续上次/基于之前”等，或 L3 任务确实可能复用研究结论时才召回。再按 owner、相关度、有效期、Top-K 和字符预算过滤；默认 Top-K 3、上下文最多 3000 字符。普通 L1 和 Smalltalk 不加载长期记忆。

### 11.5 Memory Write Gate

主模型在生成正常答案时同时输出内部 Metadata：`worth_storing`、`memory_type`、`value_score`、`stability`、`time_sensitive` 和 `topic`，不为“是否值得记”再调用一次模型。

代码 Policy 的最终判断顺序：

```text
Answer + Memory Metadata
→ Citation / Claim / Answer Verification 必须通过
→ value_score ≥ 0.75
→ stability / time_sensitive 判断长期记录或 Snapshot
→ Owner-scoped Dedup
→ Conflict Check
→ Write / Merge / Update / Skip
```

Smalltalk、一次性改写、随时可重查的简单公开事实和证据不足结论不会直接进入长期记忆。最新/当前/今年等信息优先保存为有过期时间的 Snapshot。

### 11.6 短期 Context 与长期 Memory 是否同时注入

短期 Context 每轮加载，用于理解当前会话；长期 Memory 只有 Retrieval Gate 触发时才召回。两者可以同时存在，但职责和预算独立：短期上下文默认最多 2400 字符，长期研究记忆最多 3000 字符。Personal Library 的论文原文属于 Source Knowledge，Long-Term Memory 保存 Agent 从材料中形成且验证通过的 Derived Knowledge，二者也不会混为同一张记忆表。

### 11.7 Checkpoint、暂停与续跑一致性

官方 LangGraph `SqliteSaver` 使用 `thread_id=conversation_id` 保存节点级快照，数据库为 `data/memory/langgraph_checkpoints.db`，开启 WAL；业务层另有 `pending_clarification`，保存为什么暂停以及需要用户补充什么。

续跑依靠：

- 相同 `conversation_id/thread_id` 找到会话和图状态；
- `retry_count`、`answer_reflection_count` 保存在 State，恢复时不会自动清零形成无限循环；
- 新请求显式重置本轮临时检索、答案和验证字段，避免旧状态污染；
- 工具返回统一结构并记录失败状态，当前工具以只读检索为主，重复执行风险较低。

当前最完整的恢复场景是主动澄清后继续。项目没有实现分布式 Job Queue、事件日志、幂等 Tool Commit 和 exactly-once，因此不能声称支持跨机器任意节点的严格一次长任务续跑。

### 11.8 Session、用户和全局对象隔离

`conversation_id` 用于消息与 Checkpoint 分区，`user_id` 用于 Personal Library 和 Long-Term Memory Owner 过滤；不能用 Session ID 替代用户权限。允许全局复用的对象仅限只读 Tool Registry/Router、模型或索引缓存，以及受锁保护的 Checkpointer 生命周期对象。消息、文档、答案和重试计数都在 AgentState 或 SQLite 中按 ID 隔离；SQLite Memory Store 每次操作创建独立连接，避免多个 Web 请求共享 Cursor。

生产环境还应校验会话属于当前用户、使用服务端不可预测 ID、设置过期与清理，并避免把私有回答写入公共缓存。

### 11.9 为什么当前不必强制 Redis

单机简历项目使用 SQLite 和文件缓存更简单可靠。Redis 只有在多实例部署、跨进程共享 Session、分布式锁、任务队列或高频热点缓存出现后才有明显收益。未来引入时应负责短期缓存/协调，不替代持久化知识和论文库。

---

## 12. 产品、权限、报告与部署层

### 12.1 登录与个人论文库

MVP 使用 PBKDF2 密码哈希、服务端不透明 Bearer Token。每个文档绑定 `user_id / library_id / collection_id / document_id`；上传、列表、删除和检索都进行 Owner 过滤，避免其他用户的 Chunk 进入结果。

### 12.2 报告导出

Word/PDF 报告复用已经生成并验证过的答案、Evidence、检索范围、Trace ID 和页码，不再次调用 LLM。这样导出结果与网页一致，也不会因为下载报告增加费用或产生第二版结论。

### 12.3 Docker 与 CI

Docker 镜像不打包 `.env`、API Key、本地论文、模型缓存和评测输出。Compose 挂载数据与日志，SQLite 记忆使用独立 Volume，避免 Windows bind mount 与 WAL 的兼容问题。GitHub Actions 运行基础安装、回归和部署配置检查。

### 12.4 可观测性

每次执行记录：`trace_id`、节点开始/结束、路由选择、工具名和状态、重试次数、证据数量、停止原因、模型调用数、Token 和延迟。日志不记录密钥、完整 Base64 页面或敏感绝对路径。

---

## 13. 技术栈

| 层 | 技术 | 项目中的作用 |
|---|---|---|
| Agent 编排 | LangGraph | 状态图、条件边、Checkpoint、有限恢复 |
| LLM 接入 | LangChain OpenAI-compatible | 接入百炼主模型与结构化调用 |
| 主模型 | `qwen3.7-max-2026-05-17` | 复杂分析、生成、必要 Reflection |
| 视觉模型 | `qwen3.5-ocr` | PDF 页面 OCR、布局与关键视觉信息提取 |
| API | FastAPI + Pydantic + Uvicorn | HTTP 接口、契约校验、ASGI 服务 |
| 在线论文 | arXiv、OpenAlex、Crossref、Semantic Scholar | 发现、元数据和身份补全 |
| PDF | pypdf、PyMuPDF | 全文/页码提取和关键页渲染 |
| Local RAG | BM25、FastEmbed、ONNX Runtime、MPNet、NumPy | 词法/语义召回、缓存和融合 |
| 协议工具 | MCP stdio | Paper Catalog Server、Zotero/GitHub Client |
| 数据 | SQLite、JSON/CSV/XLSX、文件缓存 | 用户/记忆/Checkpoint、评测和索引 |
| 报告 | python-docx、ReportLab 等 | Word/PDF 研究报告 |
| Web | HTML/CSS/JavaScript | Research Console 与可观测展示 |
| 测试 | Pytest + 自研 Eval Harness | 离线回归、在线能力、A/B 和 Gate |
| 交付 | Docker Compose、GitHub Actions | 可复现启动与基础 CI |

---

## 14. 测试体系与详细结果

### 14.1 测试分层

| 层级 | 作用 | 通过代表什么 | 失败代表什么 |
|---|---|---|---|
| 单元测试 | 验证单一规则、模型契约和边界 | 局部逻辑满足预期 | 可定位到具体函数/模块回归 |
| Graph 集成测试 | 验证节点、条件边和 State 交接 | 典型路径可正确串联 | 路由、状态或停止条件异常 |
| 离线能力集 | 固定输入比较策略能力 | 不依赖供应商波动，可稳定回归 | 策略或规则能力退化 |
| 在线 LLM 集 | 验证真实模型结构化理解 | Prompt/Contract 在真实服务可用 | 区分 Provider Failure 与 Capability Failure |
| Retrieval/RAG 评测 | 测 Recall、MRR、nDCG、Hit 等 | 目标论文/Chunk 排名满足门槛 | 召回、排序或数据污染问题 |
| 真实冒烟 | 跑通外部服务完整链路 | 集成、凭据、网络和真实输出可用 | 可能是能力、配置或供应商问题 |
| A/B + Promotion Gate | 判断候选是否值得晋升 | 质量提升且没有不可接受回归/成本 | 候选保留为实验，不替换当前策略 |

### 14.2 当前关键结果总表

| 测试范围 | 数据规模 | 结果 | LLM/Token | 结果说明 |
|---|---:|---:|---:|---|
| 项目完整离线回归基线 | 422 项 | 422/422 | 0 LLM | 覆盖 Graph、Tool/MCP、RAG、记忆、认证、报告、部署等 |
| PDF v2 专项 | 35 项 | 35/35 | 0 LLM | 关键页、4 类视觉 Skill、Schema、Grounding 和前端契约 |
| 受控进化与 Schema Guard 离线回归 | 21 项 | 21/21 | 0 LLM | Failure、Candidate、Gate、Registry 和真实报告适配 |
| 核心在线 LLM 能力集 | 30 题 | 29/30，96.67% | 17 次，62,525 Token | 当前落盘 JSON 的复核结果；Provider Failure 为 0 |
| 最终回答质量真实 A/B | 16 题 × 2 | 内容质量 68.44 → 92.34 | 32 次，88,440 Token | 相同证据下比较直接生成与 PaperAgent；不足披露 28.57% → 100% |
| PDF 视觉真实冒烟 | 1 条完整链路 | 1/1 | 2 次，7,549 Token | GraphRAG PDF 第 4 页，Figure Schema 与 Grounding 通过 |
| Personal + Online Hybrid | 1 条完整链路 | 通过 | 2 次，5,717 Token | 8 条证据，个人库和 arXiv 均命中，最终验证通过 |
| Research Analyzer few-shot A/B | 6 题 × 2 | 候选拒绝 | 12 次，16,150 Token | 能力提升但 1 题回归且 Token +28.92% |
| Schema Guard A/B | 6 题 × 2 | 候选拒绝 | 12 次，15,307 Token | 解析率 100%，能力不升且 Token +11.98% |
| 报告导出专项 | 13 项 | 13/13 | 0 LLM | Word/PDF 结构、中文、引用与下载路径 |

> 历史说明：首次命令行输出曾显示 27/30；修复报告导出并按保存的原始模型响应重新校验后，当前 `outputs/llm_core_eval/latest_llm_online.json` 记录为 29/30。总 Token、调用次数和总时长保持同一轮原始数据。面试和 README 应使用可追溯的 29/30，不混用历史终端摘要。

### 14.3 核心在线集验证什么

30 题覆盖研究复杂度 L1/L2/L3、Skill 选择、结构化 Plan、意图短路、查询与澄清边界。`passed` 要求该题声明的全部 checks 通过；`provider_failure_count` 单独统计超时、限流或服务异常，避免把外部故障误算成 Agent 能力失败。

结果：29 题通过、1 题能力失败、Provider Failure 0；通过率 `29 ÷ 30 × 100% = 96.67%`。17 次 LLM 调用意味着部分规则型 Case 以 0 LLM 完成。

### 14.4 检索与排序指标计算

| 指标 | 计算方式 | 解释 |
|---|---|---|
| Recall@K | Top-K 中命中的相关项数 ÷ 全部相关项数 | 应找的材料找回多少 |
| Precision@K | Top-K 中相关项数 ÷ K | 返回材料有多少真正相关 |
| Hit@K | Top-K 至少命中 1 个目标则为 1 | 目标是否进入候选 |
| MRR | 第一个相关结果排名倒数的平均值 | 目标是否排得靠前 |
| nDCG@K | 实际折损累计增益 ÷ 理想排序增益 | 多级相关性下排序质量 |
| Duplicate Rate | 重复结果数 ÷ 返回结果数 | 合并去重效果 |
| Coverage | 有合格证据的计划项数 ÷ 全部计划项数 | 研究计划是否被证据覆盖 |

### 14.5 Agent 与运行指标计算

| 指标 | 计算方式 | 用途 |
|---|---|---|
| Intent Accuracy | 正确意图数 ÷ 总 Case 数 | Smalltalk/研究任务路由 |
| Plan Accuracy | 满足预期结构和查询的 Plan 数 ÷ 总数 | 拆分和依赖正确性 |
| Route Accuracy | 正确目标节点/工具数 ÷ 总数 | Graph 与 Tool Router |
| Pass Rate | 全部必需 Check 通过的 Case 数 ÷ 总数 | 综合能力 |
| Provider Failure Rate | 外部服务失败 Case ÷ 在线 Case | 区分平台可靠性与能力 |
| Claim Support Rate | supported Claim ÷ 全部可验证 Claim | 声明证据一致性 |
| Token/Case | 总 Token ÷ Case 数 | 平均模型成本 |
| P95 Latency | 延迟排序后的 95 分位 | 尾部响应性能 |
| CV | 延迟标准差 ÷ 平均延迟 × 100% | 运行稳定性，受网络和冷启动影响 |
| Replan/Reflection Rate | 触发次数 ÷ 请求数 | 恢复机制是否过度触发 |

### 14.6 能力演进基线

早期离线 Capability Benchmark 的代表性提升：

| 模块 | 基线 → 改进 | 附加指标 | 说明 |
|---|---:|---:|---|
| Intent Router | 40.0% → 100.0% | 避免 6 次估算 LLM 调用 | Smalltalk 本地短路 |
| Query Planning | 33.33% → 66.67% | 平均查询 1.0 → 3.5 | 复杂任务覆盖提高，但曾出现 4 个简单任务过度拆分，后续增加分级约束 |
| Result Merger | 33.33% → 100.0% | 重复项 2 → 0 | 统一身份和去重生效 |
| Retry Router | 75.0% → 100.0% | 正确触发 1 次重试 | 失败恢复从无重试升级为受控重试 |

该表是固定离线样本上的模块对照，不等同于线上用户满意度；它的作用是证明各能力为什么被引入，并暴露过度规划等副作用。

### 14.7 受控进化真实 A/B

| 候选 | 解析率 | 能力通过率 | 平均 Token 变化 | P95 变化 | 逐题回归 | Gate |
|---|---:|---:|---:|---:|---:|---|
| 完整 few-shot | 66.67% → 100% | 16.67% → 66.67% | +28.92% | +12.22% | 1 | 拒绝 |
| 最小 Schema Guard | 50% → 100% | 16.67% → 16.67% | +11.98% | -25.76% | 0 | 拒绝 |

结论：few-shot 有语义收益但成本高且损伤原有 Case；Schema Guard 修复格式却没有提高任务能力。当前继续保留 zero-shot，证明进化系统不会因为单一平均指标变好而自动上线。

### 14.8 最终回答质量 A/B

16 题冻结集平均覆盖方法比较、单篇总结、多论文综合和证据不足四类。两边使用相同模型和相同论文证据：Baseline 直接回答，PaperAgent 使用 Evidence Store、Research Writer 与验证链。为避免引用要求使对比失真，主要内容指标不包含引用分。

| 指标 | Baseline | PaperAgent | 变化 |
|---|---:|---:|---:|
| 回答内容质量分 | 68.44 | 92.34 | +23.90 |
| 研究维度覆盖率 | 91.67% | 100.00% | +8.33pp |
| 关键事实覆盖率 | 56.25% | 78.12% | +21.87pp |
| 证据不足披露率（14题） | 28.57% | 100.00% | +71.43pp |
| 声明证据支持率 | 0.00% | 75.00% | +75.00pp |
| 引用准确率 / 可追溯率 | 0.00% / 0.00% | 100.00% / 100.00% | +100.00pp |

代价是平均 Token 增加 271.98%、P95 延迟增加 48.09%，因此完整 Research Writer 只用于 L3 研究任务，不能为追求质量把所有 L1 问答升级成重流程。完整方法、逐类结果、限制和命令见 `docs/ANSWER_QUALITY_AB_REPORT.md`。

### 14.9 测试用例说明与证据位置

每次本地测试由 `scripts/run_tests_with_report.py` 输出 CSV，包含用例名、所属能力、测试目的、通过代表什么、失败代表什么、耗时和结果。新增测试需同步登记到测试目录或 Catalog，防止只增加代码而没有可读说明。

主要证据：

- 全量 PDF v2 用例表：`outputs/test_reports/full_pdf_visual_v2/latest_test_details.csv`
- 受控进化用例表：`outputs/test_reports/schema_guard_evolution/latest_test_details.csv`
- 在线核心逐题结果：`outputs/llm_core_eval/latest_llm_online.json` 和 `.csv`
- 最终回答质量逐题对照：`outputs/answer_quality_ab/latest_answer_quality_ab.json` 和 `.csv`
- PDF 视觉原始摘要：`outputs/pdf_vision_smoke/latest.json`
- Hybrid 冒烟：`docs/HYBRID_SMOKE_REPORT.md`
- Retrieval/RAG Excel：`outputs/retrieval_eval/`、`outputs/local_rag/`

---

## 15. 性能、成本与可靠性

### 15.1 已有真实数据

| 场景 | 数据 | 解释 |
|---|---:|---|
| 多查询并行实验 | 约 1.54× 加速，延迟下降 35.09% | 子查询无依赖时并行，结果顺序仍保持 100% 一致 |
| 30 题在线核心集 | 435.097 秒，62,525 Token，17 次调用 | 包含规则零调用 Case 和真实模型 Case |
| 最终回答质量 A/B | Baseline 1,171 Token/题；PaperAgent 4,356 Token/题 | 内容质量 +23.90 分，但 Token +271.98%，用于证明 L3 分级路由的必要性 |
| Hybrid 冒烟 | 31.71 秒，5,717 Token | 检索 2.65 秒；Reflection 2,353 Token，占约 41% |
| PDF 视觉冒烟 | 81.668 秒，7,549 Token | OCR + 主模型两阶段，视觉任务天然更慢 |
| few-shot A/B | 平均延迟 9.64s → 11.37s | Prompt 变长带来成本和延迟上升 |
| Schema Guard A/B | P95 14.34s → 10.64s | 小样本结果，仅作候选比较，不推断长期线上收益 |

### 15.2 性能设计

- Smalltalk、规则恢复、关键页选择和大部分 Policy 为 0 LLM；
- 无依赖子查询和 Hybrid 两路使用有界异步并行；
- 在线结果、Embedding 和索引使用本地缓存；
- Dense 低置信度时复用已有排名再做 Hybrid，避免重复计算；
- 超时、重试和循环均有上限；
- 报告导出复用答案，0 额外 LLM；
- 每次调用记录 Token 和节点延迟，便于找到成本热点。

### 15.3 如何理解延迟 CV 52.25%

`CV = 标准差 ÷ 平均值`。52.25% 表示多次查询耗时波动较大，不代表平均速度一定慢。常见原因包括首次模型/索引冷启动、网络与供应商波动、不同查询命中缓存情况不同、样本过少。对于简历项目，记录并解释即可；生产优化时应区分冷/热启动，扩大重复次数并同时观察 P50/P95。

### 15.4 当前性能边界

现有数据适合证明链路可运行和优化方向，不是生产 SLA。真实在线样本量较小，受百炼、arXiv 网络和本机缓存影响；未来所有性能对比必须固定模型、数据集、并发、缓存状态和运行环境。

---

## 16. 开发迭代记录

| 阶段 | 完成内容 | 解决的问题 | 验证方式 |
|---|---|---|---|
| 1. 最小 Agent | LangGraph、Intent、Retrieve、Generate | 建立可运行状态图 | Graph 集成测试 |
| 2. 成本治理 | Smalltalk 短路、Token/节点指标 | 简单输入浪费模型 | Intent Benchmark |
| 3. 查询工程 | Rewrite、Plan、并行 Scheduler、Replan | 复杂问题覆盖不足 | Planning/Parallel 对照 |
| 4. Tool 工程 | Router、Registry、Policy、Executor、Adapter | 工具耦合与异常不统一 | Tool 契约与集成测试 |
| 5. 多源论文 | arXiv、OpenAlex、Crossref、Semantic Scholar | 单源覆盖与元数据不足 | Retrieval/Authority 评测 |
| 6. Local RAG | PDF、BM25、Dense、RRF、置信门 | 只依赖摘要、无法问全文 | Gold/Holdout/A-B |
| 7. Research Agent | L1-L3、Brief、Plan、Evidence、Coverage | 研究请求缺少结构 | 在线核心集 |
| 8. 质量恢复 | Citation、Claim、Grounding、Reflection | 生成结论不可验证 | Validator 与 Badcase |
| 9. Context/Memory | 会话压缩、Checkpoint、Long-Term Gate/RAG | 多轮丢失与记忆污染 | Memory/API 回归 |
| 10. 产品 MVP | 登录、个人库、Owner 隔离、Hybrid | 私人材料无法长期使用 | Product + Hybrid 冒烟 |
| 11. MCP | Paper Catalog、Zotero、GitHub | 工具跨进程和外部复用 | stdio/MCP 集成测试 |
| 12. Multi-Agent | Planner/Executor/Reviewer 有界交接 | 展示复杂职责分离 | Orchestrator 回归 |
| 13. 多模态 | 自动关键页、图/表/曲线/公式 Skill | PDF 只会提取文字 | 35 项离线 + 在线冒烟 |
| 14. 报告与前端 | 美化 Console、Markdown 渲染、Word/PDF | 展示和交付不足 | 13 项报告专项 |
| 15. 工程交付 | Docker、CI、Release Checklist | 环境不可复现 | 部署配置与健康检查 |
| 16. 受控进化 | Failure、Candidate、Gate、Registry、真实 A/B | Prompt 迭代缺少回归控制 | 21 项回归 + 两轮 A/B |
| 17. 最终答案评测 | 16 题直接生成 vs PaperAgent 真实 A/B | 无法证明复杂工作流是否改善最终回答 | 内容质量 +23.90 分，不足披露达到 100% |

迭代原则：每项新能力必须说明问题、实现、指标和边界；不再为了“看起来先进”持续增加研究型模块。

---

## 17. 后续扩展路线

### 17.1 优先级 P0：完成交付而非继续堆模块

1. 在干净 Windows 环境按 README 冷启动一次；
2. 确认 GitHub Actions 在远端 master 绿灯；
3. 固化 3～5 分钟演示数据和讲解顺序；
4. 保持总文档、测试表和代码版本一致。

### 17.2 优先级 P1：产品化增强

- Personal Library 增加 Collection、标签、搜索、批量导入和 Zotero 同步；
- 对象存储保存 PDF，PostgreSQL 保存用户/文档元数据；
- 完整 RBAC、Token 过期/刷新、审计和限额；
- 长任务改为 Job API + 队列 + 进度事件，而不是保持 HTTP 半小时连接；
- 报告模板、异步导出和历史报告中心；
- 前端增加研究计划编辑、证据展开和失败原因引导。

### 17.3 候选外部数据源

| 候选 | 价值 | 接入注意 |
|---|---|---|
| PubMed / Europe PMC | 生物医学论文和结构化元数据 | 领域路由、许可、全文可用性 |
| OpenReview | ICLR 等评审、讨论和版本 | 区分论文正文与评审意见 |
| Papers with Code | 论文、任务、数据集和代码关联 | 身份对齐与链接时效 |
| Unpaywall | 开放获取全文定位 | DOI 覆盖、版权和下载策略 |
| CORE | 开放论文聚合 | API 配额、重复和质量控制 |
| Crossref/SS 深化 | 引文网络和出版身份 | 限流、缓存和权威冲突策略 |
| Zotero | 用户私人文献资产 | OAuth、增量同步和 Owner 隔离 |
| GitHub | 实现仓库与 README 证据 | 代码证据不能冒充论文结论 |

新增数据源统一实现 Adapter，进入 Tool Registry/Policy/Executor；必须测试命中率、元数据正确率、重复率、P95、失败率和成本，不直接堆进默认多源模式。

### 17.4 RAG 候选选型框架

不预先写死 GraphRAG、LightRAG、向量数据库或 Reranker。建立相同学术任务集，比较：

- 单篇事实定位：Recall@K、MRR、页码正确率；
- 跨论文比较：实体/维度 Coverage、Claim Support；
- 全局综述：主题覆盖、Faithfulness、人工可用性；
- 更新：新增/删除论文耗时与索引一致性；
- 工程：索引大小、构建成本、查询 P95、Token；
- 隔离：Owner Filter 是否在召回前生效；
- 运维：失败恢复、备份和迁移复杂度。

候选可包括 BM25、Dense、Hybrid、Cross-Encoder Rerank、GraphRAG、LightRAG、pgvector、Qdrant、Milvus 等。只有候选显著改善目标任务且满足成本门槛才晋升。

### 17.5 记忆与基础设施扩展

- Memory Need Detection 增加更细的任务类型特征，但优先规则，不为每轮增加 LLM；
- Dedup/Conflict 增加 Embedding 和时间版本链；
- Redis 仅在多实例共享 Session、缓存、锁或队列时引入；
- PostgreSQL 负责持久业务数据，Redis 负责短时状态，向量库负责规模化语义索引；
- Team/Organization、Shared Collection 和 RBAC 在个人库稳定后再做。

### 17.6 PDF 与多模态扩展

- 检测并裁剪单个 Figure/Table 区域，减少整页图像 Token；
- 跨页表格拼接和多图关联；
- 图表数据结构化抽取与跨论文实验对齐；
- Visual Evidence 单独索引和召回；
- 表格数值一致性校验；
- 所有升级继续保留图片出站确认、页数预算和 Grounding。

### 17.7 性能扩展

- 增加冷/热启动分离的 Benchmark；
- 记录 P50/P95/P99、缓存命中率、队列时间和每节点 Token；
- 对 Reflection 建立触发收益率，避免无收益的第二次生成；
- Provider 限流和熔断、批量 Embedding、连接池；
- Prompt Cache 只缓存稳定前缀，将动态用户证据放后部提高命中率；
- 大工具输出先落 Evidence Store/对象存储，再摘要和 Top-K 注入，不把完整 JSON 塞入上下文。

### 17.8 明确暂缓

- 无边界全自主 Agent Loop；
- 全量 Master + 多 Sub-Agent 自由协商；
- 自动修改代码、权限或生产配置的“自进化”；
- Multi-Trajectory/Best-of-N 默认运行；
- 在没有用户量前建设复杂 Redis Stream、分布式事件总线和 Kubernetes；
- 只为技术名词而替换已满足需求的 RAG。

---

## 18. 运行、测试与演示

### 18.1 本机启动

```powershell
Set-Location D:\langgraphproject
conda activate paper_agent
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -m uvicorn app.api:app --host 127.0.0.1 --port 8000
```

打开：

- Research Console：`http://127.0.0.1:8000/`
- Swagger：`http://127.0.0.1:8000/docs`
- 健康检查：`http://127.0.0.1:8000/health`

### 18.2 核心模型配置

```env
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_API_KEY=你的百炼_API_Key
MODEL_NAME=qwen3.7-max-2026-05-17
PDF_VISION_ENABLED=false
PDF_VISION_MODEL_NAME=qwen3.5-ocr
```

OpenAlex 不使用百炼 Key；百炼 Key 只用于模型。OpenAlex Key 为其独立可选凭据，`OPENALEX_MAILTO` 是请求中用于标识联系邮箱的礼貌池信息，不是密钥。

### 18.3 Docker

```powershell
Copy-Item .env.example .env
docker compose up --build -d
docker compose ps
```

### 18.4 一键测试

日常开发优先运行受影响模块，不必每次付费跑完整在线集：

```powershell
python -m pytest -q
```

需要生成带“测试作用/通过含义/失败含义”的本地表格：

```powershell
python .\scripts\run_tests_with_report.py
```

真实在线核心集（会消耗 Token）：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_llm_online_eval.ps1
```

受控策略进化离线演示：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_evolution_cycle.ps1
```

PDF 与 Hybrid 真实冒烟必须显式确认在线调用，避免误花费 Token。

### 18.5 推荐演示顺序

```text
1. 输入 hi → 展示 0 LLM 短路
2. 加载零 API 示例轨迹 → 展示完整 LangGraph 和 Evidence
3. 登录并上传论文 → 展示 Owner-scoped Personal Library
4. 运行 Personal + Online Hybrid → 展示私人 + 公开知识
5. 分析 GraphRAG PDF 架构图 → 展示多模态和 Grounding
6. 导出 Word/PDF → 展示产品交付
7. 打开进化报告 → 展示候选因回归/成本被 Gate 拒绝
```

---

## 19. 项目目录结构

```text
paper-agent/
├─ agent/                 # AgentState、LangGraph 主图与路由
├─ app/                   # FastAPI、Pydantic API、Web 静态页面
├─ context/               # 上下文构建与压缩相关逻辑
├─ core/                  # 配置、日志、Trace、LLM Usage
├─ document_loader/       # PDF 文本加载
├─ eval_harness/          # 冻结数据集、指标、在线/离线评测
├─ evolution/             # Failure、Candidate、Promotion Gate、Registry
├─ local_rag/             # Chunk、BM25、Dense、RRF、索引缓存
├─ mcp_servers/           # 本地 MCP Server
├─ memory/                # 会话、Checkpoint、LLM Wiki、长期记忆
├─ metrics/               # 运行指标
├─ multi_agent/           # Planner/Executor/Reviewer 有界编排
├─ nodes/                 # LangGraph 业务节点
├─ product/               # 用户、认证、个人论文库
├─ prompts/               # Prompt 与版本契约
├─ reports/               # Word/PDF 报告生成
├─ research/              # Analyzer、Plan、Schedule、Evidence、Coverage、Writer
├─ retrieval/             # 检索策略、合并、重排与恢复
├─ skills/                # 科研回答与 PDF 多模态 Skill
├─ tools/                 # Tool/MCP Router、Registry、Policy、Executor、Adapters
├─ validators/            # 引用、声明、答案和 Grounding 验证
├─ scripts/               # 一键运行、评测与报告脚本
├─ tests/                 # 单元与集成测试
├─ data/                  # 本地论文、SQLite、模型/索引缓存（不提交大文件）
├─ outputs/               # JSON/CSV/XLSX 测试和真实实验产物
├─ docs/                  # 本总说明与专项历史报告
├─ Dockerfile
├─ docker-compose.yml
├─ requirements.txt
└─ README.md
```

---

## 20. 已知边界与诚实表述

- 当前是个人简历项目，不宣称已经达到生产 SLA 或大规模多租户能力；
- Multi-Agent 是有界逻辑角色协作，不是自治 Agent 集群；
- RAG 是 BM25 + Dense + RRF，不是 GraphRAG 或 LightRAG；
- MCP Paper Catalog 是本项目自建工具，不是官方论文搜索服务；
- 真实在线评测样本有限，不能外推为所有研究问题准确率；
- PDF 视觉当前按页面分析，不能保证读取极小、模糊或跨页图表；
- Checkpoint 支持续跑，但尚未实现 Redis Stream 式长任务事件流和多实例 exactly-once；
- 受控进化只生成和评估候选，不自动训练、改代码或上线；
- 个人库认证是 MVP，公网生产部署前仍需更完整的 Token 生命周期、RBAC、对象存储和安全审计。

---

## 21. 专项文档与原始证据索引

本文件是唯一总说明，以下只作为更细实现或历史实验凭证：

- `ARCHITECTURE_MODULE_GUIDE.md`：按节点展开的历史架构详解；
- `PROJECT_INTERVIEW_QA.md`：与项目有关的面试题回答；
- `CONTROLLED_EVOLUTION.md`：受控进化实现契约；
- `REAL_EVOLUTION_TEST_REPORT.md`：few-shot 真实 A/B；
- `SCHEMA_GUARD_EVOLUTION_REPORT.md`：Schema Guard 真实 A/B；
- `ANSWER_QUALITY_AB_REPORT.md`：最终回答质量真实 A/B、成本与边界；
- `PDF_VISUAL_V2_REPORT.md`：PDF 多模态实现和实测；
- `HYBRID_SMOKE_REPORT.md`：Personal + Online 真实链路；
- `RELEASE_CHECKLIST.md`：发布核验；
- `ROADMAP.md`：历史规划和讨论记录，不再作为当前状态唯一依据；
- `outputs/`：逐题 JSON/CSV/XLSX 原始证据。

维护规则：新增模块时先更新本文件对应架构、模块、测试和边界；专项报告只记录实验细节，不再另建一份相互竞争的“完整项目说明”。

---

## 22. 项目相关面试重点工程决策

本章将高频面试追问映射到当前代码事实。更适合逐题背诵的版本见 `PROJECT_INTERVIEW_QA.md`；这里解释设计之间的关系。

### 22.1 为什么是 Workflow-first，而不是自治 Agent 集群

论文研究的主阶段相对稳定：理解、规划、检索、证据、生成、验证。权限、超时、重试和证据合法性必须由代码保证；开放目标理解和多论文综合才使用模型。因此主体使用带条件分支的 LangGraph Workflow，L3 仅增加 Planner、Executor、Reviewer 三段角色交接。

```text
Planner：生成 Research Brief、DAG 和执行波次，不直接调用工具
→ Executor：执行只读检索并写 Evidence，不决定答案是否可信
→ Reviewer：检查 Coverage、Citation、Claim 和 Answer，不重新规划全部任务
```

角色之间通过结构化 AgentState 通信，不共享自由自然语言聊天室。这样可以复现 Badcase、定位责任节点、控制循环预算；代价是适应完全未知任务的自由度低于自治 Agent Swarm，但更符合当前科研研究场景和简历项目规模。

### 22.2 execCtx 在项目中如何落地

项目没有单独命名为 `execCtx` 的类，其职责由 `PaperAgentService + AgentState + LangGraph configurable` 共同承担：

| 维度 | 字段示例 |
|---|---|
| 身份 | `trace_id / user_id / conversation_id` |
| 输入 | `query / resolved_query / pdf_path / retrieval_scope` |
| 计划 | `task_level / research_plan / research_schedule` |
| 执行 | `documents / evidence_store / tools_used / retry_count` |
| 质量 | Coverage、Citation、Claim、Grounding、Answer Verification |
| 成本 | `llm_usage / token_usage / node_timings` |
| 持久化 | `configurable.thread_id=conversation_id` |

每个节点接收 State 快照并只返回增量字段，避免把请求状态放在可变全局变量中。AgentState 是运行事实容器，不等于模型上下文；Context Policy 再从中选择当前 Skill 所需信息。

### 22.3 首次提问、多轮补充和修改诉求

- 首次提问：创建会话与空状态，从 Intent 开始；Smalltalk 可以本地结束。
- 多轮补充：复用 `conversation_id`，加载最近消息、旧摘要、研究状态和 Checkpoint；Clarification 恢复“第二篇/刚才那个方法”等指代。
- 修改诉求：新消息作为新请求进入，`original_query` 与 `resolved_query` 分开；一次性缩写不写长期记忆，改变研究目标则重新做复杂度与检索分析。
- 无法恢复：保存 `pending_clarification` 并向用户提问，不猜测缺失实体。

### 22.4 ReAct、Plan-and-Execute 与有限 Loop

ReAct 在行动和观察之间动态调整，适合路径不确定、工具反馈会改变下一步的任务；Plan-and-Execute 先拆解依赖再执行，适合目标和子任务可以预先定义的复杂研究。PaperAgent 采用混合方式：L3 先生成受限 DAG，再在检索质量不足时基于观察定向 Replan。

项目没有无限 Thought/Action Loop，而是两个可计数闭环：

```text
Retrieval：Evaluate → Replan → Retrieve，最多 1 次
Answer：Verify → Reflection → Verify，最多 1 次
```

重试必须有明确失败类型和现有修复依据；Reflection 没有提高验证分时恢复原答案。这样解决路径震荡、重复搜索和成本不可预测问题。

### 22.5 异步并行与长耗时工具

当前并行发生在无依赖子任务、Personal/Online Hybrid 分支和可选多来源检索；Scheduler 保证综合任务等待依赖完成，并限制最大并发。当前 FastAPI 主图仍是同步请求模型，Tool Executor 适合秒级检索并有超时，不支持半小时任务。

如果扩展长任务，正确方案是：

```text
POST 创建 Job → 返回 job_id
→ Worker 执行并持久化 progress / heartbeat / checkpoint
→ SSE、WebSocket 或轮询读取状态
→ completed 后主图只消费 Evidence 引用
```

还需幂等键、取消、租约、超时和失败重试。仅把 HTTP/Tool timeout 改成 1800 秒会占用 Worker，断线后也无法可靠恢复，因此不是可接受方案。

### 22.6 大量 Tool 和 Skill 如何避免 Token 爆炸

当前不会把所有 Tool Schema 和 Skill Prompt 塞给模型：

1. Retrieval Router 先确定 Online/Personal/Hybrid/PDF 范围；
2. Tool Policy 按来源、权限、配置和风险过滤；
3. Tool Router 以 `capability + source` 选择一个小候选；
4. Skill Router 根据任务等级、主 Skill 白名单和 PDF 意图只选择一个主 Skill；
5. Context Policy 只加载该 Skill 需要的历史、文档、PDF 和元数据。

如果扩展到 500 Tool/500 Skill，应建立分层 Capability Catalog：先做领域/权限粗召回，再对 Top-K 描述进行语义或模型选择；工具 Schema 延迟加载，常用能力缓存，选择结果用 Tool Selection Eval 回归。不能依靠模型在一次 Prompt 中阅读全部描述。

### 22.7 大工具输出和大 JSON 如何处理

外部结果先由 Adapter 转成统一 Paper/ToolResult，再进入 Evidence Store；只向 Writer 注入 Top-K、截断片段、来源和 Evidence ID。Local RAG 结果保存 `document_id/chunk_id/page/score`，不把完整索引或供应商 JSON 放进 Prompt。

更大规模时应将原始输出放入对象存储或数据库，在 State 中只留引用、统计和游标，使用分页或二次检索按需读取。大 JSON 直接进入模型会增加 Token、降低中间字段注意力、造成截断，并让错误重试重复传输同一数据。

### 22.8 Tool 的 Session 隔离与有状态执行

公开 arXiv/日期等只读工具可以不依赖 Session；个人论文库、记忆删除和报告资产必须同时校验 `user_id` 与资源 Owner。Tool 实现不直接读取全局当前用户，而由 Executor 显式传递经过 Policy 检查的上下文，从而降低工具与会话层耦合。

有状态或有副作用 Tool 若未来加入，应使用 `trace_id + task_id + operation` 形成幂等键，写入执行记录后再执行，并在重试前查询状态。当前外部工具主要只读，因此项目没有宣称已经实现 exactly-once 副作用语义。

### 22.9 RAG 相似度、召回观察与技术选型

Dense Retrieval 使用 L2 归一化后的向量相似性，本质上对应余弦方向相似度；BM25 使用词项统计，RRF 按名次融合两路，避免直接混合不可比原始分数。余弦更关注方向、对文本长度不敏感；欧氏距离同时受幅度影响，向量归一化后两者排序关系接近。

每个召回 Chunk 保留文档、Chunk、页码、正文片段、来源和分数；Trace 记录查询、Dense Top-1、margin、Dense/Hybrid 路由原因和缓存命中，Evidence 面板展示最终进入生成的内容。这样 Badcase 可以区分“没有召回、排序靠后、Coverage 误判、还是 Writer 没使用证据”。

GraphRAG、LightRAG、Reranker 和向量数据库均不写死。候选必须在相同事实定位、跨论文比较和全局综述集上比较 Recall/MRR/nDCG、Claim Support、构建更新成本、P95、Token 与 Owner 隔离，再决定是否替换当前 Hybrid RAG。

### 22.10 缓存与 Prompt Cache

当前已实现：在线论文结果缓存、Dense 向量/索引缓存、FastEmbed 模型缓存和 PDF 页面 PNG 缓存。缓存键需要包含规范化查询、Provider、模型、Parser、Chunker 和版本 Fingerprint；公共检索缓存与用户私有数据必须分开。

项目没有实现模型供应商级 Prompt Cache，因此不把它写成已落地能力。若供应商支持，稳定 System Prompt、Tool/Skill Contract 应放在前缀，动态用户问题和 Evidence 放后部；同时版本化 Prompt，避免策略变更后错误命中旧前缀。

### 22.11 Badcase 如何定位和回流

定位顺序不是先改 Prompt：

```text
意图/澄清错 → 看 Router 与解析置信度
计划错 → 看 Research Analysis、Plan、Validator、Schedule
工具错 → 看 Tool Route、参数、权限、超时和错误分类
检索错 → 看 Chunk 排名、Top-1/margin、Coverage 和数据污染
证据足但回答错 → 看 Skill Context、Citation、Claim 和 Answer Verify
记忆污染 → 看 Retrieval Gate、Owner、Write Gate、Dedup/Conflict
```

Failure Dataset 保存 Case、Trace、责任模块和失败类型；候选只能修改 Allowlist 内 Prompt/Policy/Routing/RAG。相同冻结集生成 Baseline/Candidate Scorecard，Promotion Gate 要求质量提升、逐题零回归、Critical/Safety 不退化、Provider Failure 不增加，并限制 Token 和 P95。真实 few-shot 与 Schema Guard 候选均因回归、收益或成本不满足而被拒绝，说明闭环会阻止负优化。

### 22.12 哪些面试题不属于本项目

PaperAgent 没有实现 Redis Stream 持久事件流、Redis Pub/Sub 游戏平台、Coding Agent 沙箱、多人并发修改文件、Agentic RL、SFT 子 Agent、Hermes 自进化或 OpenClaw/Claude Code 源码复刻。这些可以讨论通用设计，但不能描述成 PaperAgent 项目经验。项目真实边界是单机 SQLite、同步短任务、只读工具为主、有界角色协作和受控策略候选评测。
