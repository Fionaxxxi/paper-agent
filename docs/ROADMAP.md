# PaperAgent 开发路线图

本文档是项目后续能力升级计划的唯一正式来源。开发应按照下方依赖顺序推进，后续阶段不得绕过前置阶段建立的接口、评测门槛或安全控制。

## 当前执行版路线（V3，优先级高于下方历史规划）

> 下方原整体扩展计划继续作为技术储备和设计参考；从本节发布起，只有本节列入“当前交付主线”的能力才默认进入实施。这样做不是削弱 Agent，而是把特色集中在能够完成、演示和解释的闭环上。

### 当前唯一产品主线：证据驱动的轻量 Research Agent

PaperAgent 后续不再以“增加更多论文问答功能”为主目标，而是以完成复杂研究任务为核心差异化：把用户的模糊研究目标转化为结构化 Research Brief 和受限计划，使用在线论文、全文 RAG 与 MCP 收集证据，检查研究问题覆盖和 Claim–Evidence 关系，最终交付带引用的中文研究报告。

```text
复杂研究意图
→ 结构化 Research Analysis
→ Research Brief
→ 受限 Research Plan
→ Tool / MCP / RAG 证据收集
→ Evidence Coverage
→ Literature Review / Critique
→ Claim / Citation Verifier
→ 有限 Reflection
→ 可追溯中文研究报告
```

会话记忆、上下文压缩、科研 Skill、外部 MCP 和多模态 PDF 都是这条主线的支撑能力；只有能提升研究计划、证据质量、报告可靠性或演示完整性的功能才进入当前交付。普通论文搜索和问答继续作为 L1/L2 快速路径，不被高成本 Research Graph 替代。

### 项目保留的核心特色

```text
LangGraph Graph Engineering（显式状态、条件路由、恢复边和有限循环）
→ 统一 Tool / MCP 治理（注册、权限、参数校验、超时、重试、观测）
→ 在线多源检索 + 置信度门控的本地 Hybrid RAG
→ Verifier + 单次有限 Reflection 修复
→ 结构化记忆 + Markdown LLM Wiki
→ 科研 Skill + 分级任务路由 + 轻量深度研究模式
→ Research Brief + Planner / Executor / Reviewer + Evidence Coverage
→ Zotero / GitHub 只读外部 MCP
→ 单页多模态 PDF 分析
→ Web 演示、Docker 和基础 CI
```

这条主线仍能完整体现一个 Agent 项目的关键能力：会规划、会选工具、会检索、会验证、会恢复、会记忆、会协作，并且每个决策都能在 LangGraph 状态和执行轨迹中解释。

### 当前交付主线与顺序

| 顺序 | 阶段 | 交付边界 | 项目价值 |
|---:|---|---|---|
| 1 | MCP 路由收口（已完成） | 已补齐显式 MCP Router 场景、错误映射和调用元数据；保留原生工具与 MCP 双通道 | 展示协议解耦与工具治理，而不是为了 MCP 而 MCP |
| 2 | Verifier + 有限 Reflection（v1 已完成） | 已对空答案、完整度、任务结构和论文证据信号做确定性验证；有修复证据时最多调用 LLM 修复 1 次，无改善恢复初始答案 | 形成可解释的质量控制和失败恢复闭环；后续再扩展 Claim/Citation 精细验证 |
| 3 | 结构化记忆 + LLM Wiki（v1 已完成） | SQLite 保存消息和研究上下文并提供预算压缩；Markdown Wiki 只发布通过验证且有论文证据的成果；官方 LangGraph SqliteSaver 按 thread_id 保存节点级 State。语义摘要按真实长会话需求再晋升 | 展示跨轮连续性、图状态恢复与可审阅研究成果，同时保持数据透明、可删除、易演示 |
| 4 | 科研型 Skill + 结构化输出 | 优先实现 `LiteratureReviewSkill` 与 `PaperCritiqueSkill`；实验建议并入批判分析，报告排版并入综述输出 | 用少量高价值 Skill 覆盖真实科研任务 |
| 5 | 轻量深度研究模式（Citation Validator v1 已完成） | 已增加 L0～L3 分级、Research Analyzer、Plan Validator、有界调度、Evidence Store、覆盖门控、受约束报告生成和逐引用确定性校验；下一步复测真实Writer并决定受限修复策略 | 把前述能力组合成可交付带引用研究报告的差异化闭环 |
| 6 | 外部 MCP | 先接只读 Zotero，再接只读 GitHub；分别服务个人文献库和论文代码仓库 | 证明 MCP 的跨应用复用价值 |
| 7 | 单页多模态 PDF | 用户指定代表性页面，渲染后交给视觉模型分析图、表或公式，并保留页码依据 | 以可控成本展示真正的多模态能力 |
| 8 | 工程化交付 | 完善 Web 轨迹展示、Docker、基础 CI、中文使用说明和一组端到端演示案例 | 让项目可运行、可展示、可复现 |

阶段 3～5 共同组成 Research Agent MVP，不应被理解为三个互不相关的功能阶段：

```text
阶段 3：提供研究会话连续性、摘要、预算上下文与 Checkpoint
→ 阶段 4：提供 Literature Review / Critique 的结构化研究产物
→ 阶段 5：把 Analyzer、Brief、Plan、Evidence、Writer、Verifier 连接成 Research Graph
```

Research Agent MVP 完成后，项目的首要演示案例固定为：

> 调研近年具有研究价值的 Agent 架构方向，检索代表论文，按照成熟度、创新空间、工程价值、可评测性与未来潜力比较，并输出带证据和引用的中文研究报告。

这个案例必须展示任务分级、研究目标提取、计划、工具调用、证据覆盖、一次定向 Replan、报告验证、停止原因、Token/延迟和最终引用，而不只展示最终文本。

GraphRAG 不作为当前必做主线。只有当固定测试中的“跨论文关系与全局归纳”任务明显暴露 Hybrid RAG 的不足时，才实现一个小型 `GraphRetriever` PoC，并通过相同接口比较；不预先建设 GraphRAG、LightRAG、Dense RAG 的完整研究矩阵。

保留一个可选的特色增强项：人工门控的离线策略改进。系统可以根据失败轨迹提出 Prompt、路由阈值或查询模板候选，在少量固定案例上对比，由人批准后版本化启用并可回滚；不允许 Agent 自动修改生产代码或自行上线策略。

### 工作流分级与有限 Agent Loop

参考 HTC Research Graph 的边界设计，但只吸收适合 PaperAgent 的部分。系统共用 Tool、RAG、Evidence、Memory 和 Trace 基础设施，并按照任务复杂度选择最小充分流程：

```text
L0 Direct
→ 问候、感谢、身份和固定帮助；本地返回，不调用 LLM 或工具

L1 Fast Research QA
→ 单一明确论文问题；一次分析、最多一次检索、生成和验证

L2 Standard Research
→ 比较、总结和少量子问题；查询计划、受限并行、证据合并、生成和验证

L3 Deep Research
→ 多来源调研、技术选型或正式综述；Research Brief、任务计划、证据覆盖和研究报告
```

普通请求不得未经明确规则和预算判断自动升级成高成本 L3。第一版 L3 只允许最多 5 个研究任务、并行数 2，输出中文 Markdown；不实现任意 DAG、通用 Supervisor 或角色自由对话。

系统保留两个基础有限循环，并在 L3 中组合使用：

```text
Loop A：Retrieval Replan（已有第一版）
检索证据不足 → 按失败类型修改查询或来源 → 最多重新检索 1 次

Loop B：Answer Reflection（下一阶段）
答案验证失败 → 生成结构化修复指令 → 最多重新生成 1 次 → 再验证
```

L3 深度研究增加受限研究回边：计划不合法最多修复 1 次；Evidence Coverage 不足最多补充计划 1 次；报告验证失败最多修复 1 次。各回边独立计数，但一次执行必须受统一 Token、工具调用、时间和总迭代预算控制，不能彼此嵌套重启完整流程。

所有循环都必须记录 `failure_type`、触发证据、采取动作、前后评分、额外 Token/延迟和 `stop_reason`。出现无可用证据、相同失败重复、质量没有改善或预算耗尽时停止，并返回当前最佳答案或明确的证据不足说明。

### 轻量深度研究模式目标流程

```text
复杂研究请求
→ Task Level Router（L3）
→ Research Brief（目标、范围、研究问题、来源、输出要求）
→ Research Planner（最多 5 个带简单依赖的任务）
→ Plan Validator（空任务、重复、循环依赖和预算检查）
→ Executor（最多并行 2 个，调用现有 Tool / MCP / RAG）
→ Evidence Store（标准化、去重、来源和 Claim–Evidence 关联）
→ Coverage Gate（逐研究问题检查证据覆盖）
→ 必要时定向 Replan 1 次
→ LiteratureReviewSkill 生成中文 Markdown 报告
→ Citation / Claim Verifier
→ 必要时 Reflection 修复 1 次
→ 保存报告与 Checkpoint
```

第一版不单独建设完整 Research Job 平台。先复用 FastAPI 请求、LangGraph 状态和 SQLite Checkpoint；只有真实任务证明同步请求不足时，再晋升为异步 Job API、进度事件流和中断恢复。

### 明确暂缓的研究型能力

- 跨任务自动 Reflexion 经验晋升、全自动 Agent 自进化和受控在线适应；
- 八角色分层 Multi-Agent、角色自由辩论、通用 Supervisor、任意动态 DAG 和 Multi-Trajectory / Best-of-N 大规模候选搜索；
- 自动解析整篇论文全部图表、公式和版面的完整多模态流水线；
- 在没有真实并发和共享缓存需求前引入 Redis；
- GraphRAG / LightRAG / 多 Embedding / 多重排器的全组合选型平台；
- 将 PaperAgent 的全部能力暴露为大型 MCP Server，或继续扩张外部 MCP 清单；
- 为每个小改动建立研究级数据集、独立留出集和多进程性能实验。

这些能力没有被否定；当主线完成、出现明确需求且能产生可演示收益时，再从技术储备中晋升。

### 按风险分级的测试原则

| 变更类型 | 最低验证要求 | 报告形式 |
|---|---|---|
| 普通实现、小型 Skill 或文档调整 | 2～5 个代表性测试，必要时加 1 个 Smoke Test；每个案例记录目的和结果含义 | 测试输出或中文 Markdown 记录 |
| 工作流、权限、记忆和失败恢复 | 定向单元测试 + 1 条集成路径 + 1 条失败/停止路径 | 中文 Markdown 汇总 |
| 检索算法、模型或路由策略变更 | 使用小型固定样本比较质量、回归和延迟，确认没有明显退化 | 一份阶段对比表 |
| 意图、任务分级或 Agent 路由 | 固定人工标注集，检查准确率、研究请求误短路率、错误升级率、无效 LLM/工具调用率和路由延迟 | 一份阶段对比表 |
| Verifier / Reflection / Agent Loop | 固定缺陷案例，检查缺陷识别准确率、修复成功率、正确答案破坏率、停止率、额外 Token 和延迟 | 中文 Markdown 汇总 |
| 深度研究模式 | 2～3 个代表性复杂任务，分别覆盖正常完成、证据不足与预算停止；检查研究问题覆盖率、引用有效率、任务完成率和恢复次数 | 中文阶段报告 |
| 里程碑或发布版本 | 完整回归，并更新测试用例说明与 Excel 汇总 | Excel + 中文阶段报告 |

因此，后续新增测试仍必须说明“测试什么、为什么测试、通过或失败代表什么”，但不再要求每次小改动都生成 Excel；Excel 只在里程碑统一更新。

准确度和性能测试不推迟到项目最后：每完成 Router、Verifier、Loop、Memory 或 Research Graph 中的一个可独立节点，立即执行该节点的固定案例与一条上下游集成路径；阶段结束再进行少量真实 LLM 冒烟，最终里程碑只负责完整回归和汇总，不负责第一次发现模块问题。

## 当前能力基线

项目当前已经具备：

- 对问候、感谢和身份问题进行本地意图路由；
- 基于规则的查询复杂度分类与动态查询规划；
- 带来源隔离 JSON 缓存和静态兜底文档的 arXiv / OpenAlex 可配置检索，默认仍使用 arXiv；
- 统一 ToolSpec、ToolResult、Tool Registry、Tool Router、Tool Executor、只读 ToolPolicy，以及 arXiv / OpenAlex Native Adapter；
- 支持 `arxiv`、`openalex`、`multi` 三种模式的多查询结果合并与 DOI 优先跨源去重；
- 带有限重试的检索质量评估；
- QA、总结、比较、引用、研究方向推荐和 PDF 阅读技能；
- 按节点统计 LLM Token、延迟、失败和成本所需的用量数据；
- 确定性离线能力基准测试和单元测试 Excel 报告。

当前主要限制：

- 已接入 OpenAlex 原生工具和多源编排，但尚未在真实标注问题集上证明其相对 arXiv 的在线召回、质量、延迟和额度净收益，因此默认模式仍为 arXiv；
- 尚未建立完整的本地 RAG 链路，当前优化主要属于 LangGraph 查询规划、多查询检索、结果合并和有限重试；
- 当前注册了 arXiv 与 OpenAlex 两个原生工具，尚未接入 Semantic Scholar、Crossref、PubMed 和 MCP 工具；
- Tool Router 仍是确定性来源映射，尚未加入数据源可用性、成本、限流和质量驱动选择；
- 当前入口意图仅对高置信度闲聊做精确规则匹配，查询改写和复杂度规划也主要依赖规则；`reason` 位于检索之后，查询规划通常无法直接利用正式 `task_type`，尚未建立规则与 LLM 协作的统一任务分析器；
- LangGraph 尚未配置持久化检查点；
- 当前会话记忆使用 `data/memory/{conversation_id}.json` 文件保存，只读取最近 6 条消息；尚无摘要、语义召回、并发写入保护、过期、删除和隐私生命周期管理；
- 评估主要关注检索质量，还没有完整评估最终答案质量；
- 重试还不会产生结构化批评，也不能按照失败类型选择恢复路径；
- 成功与失败轨迹尚未转化为经过验证的可复用经验。

## 总体目标与项目定位

后续开发不再只是继续增加单个 Skill，而是围绕工具治理、质量控制、上下文工程、结构化记忆、多源检索、多模态理解、多 Agent 协作、自动化评测和受控自进化进行系统升级。

项目的核心工程特色确定为：

```text
Graph-Orchestrated
→ 使用显式状态图组织规划、工具、检索、生成、验证和恢复

Harness-Driven
→ 每次能力升级都有测试、指标、对照实验、版本记录和回滚

Tool-Augmented
→ 通过统一 Tool / MCP 接入论文数据源和外部能力

Memory-Enhanced
→ 通过受控分层记忆积累对话、论文知识和经过验证的策略经验

RAG-Optional and Evaluated
→ RAG 组件可插拔，具体技术通过项目评测选择，不预先写死
```

推荐项目定位：

> 以 LangGraph 工作流图工程和 Harness 驾驭工程为核心的科研论文 Agent。

英文定位：`A graph-orchestrated and harness-driven research paper agent.`

这里的 Graph Engineering 当前主要指 Agent Workflow Graph Engineering，而不是知识图谱工程或 GraphRAG 工程。三类“图”必须在设计、文档、代码命名和评测中明确区分：

```text
工作流图工程
→ LangGraph 节点、状态、条件边、循环、子图、检查点和失败恢复

知识图谱工程
→ 论文、作者、方法、数据集、实验、引用等实体与关系

GraphRAG 工程
→ 知识图谱索引、社区发现、图检索及图与文本联合生成
```

项目当前已具备第一版工作流图骨架；知识图谱和 GraphRAG 仅作为后续经过评测才能晋升的候选能力。

最终目标是将 PaperAgent 从：

```text
多 Skill 论文分析助手
```

升级为：

```text
多 Skill
+ 多工具与 MCP
+ 多源与本地知识库
+ 多模态论文理解
+ 多 Agent 协作
+ 自动化评测与低幻觉控制
+ 可测量、可回滚的 Agent 自进化
→ 科研论文智能体平台
```

## 原整体扩展计划完成情况

| 能力方向 | 当前状态 | 已有基础 | 主要缺口 |
|---|---|---|---|
| Eval Harness | 部分完成 | 已有离线 Benchmark、案例、Runner、Validator、报告和 Excel 测试结果 | 增加服务级、在线和 CI 回归评测 |
| Verifier | 部分完成 | 已有答案、引用、PDF 依据和检索 Validator | 接入最终答案流程，补充统一评分与失败路由 |
| Context Engineering | 部分完成 | 已有 Context Builder、Policy 和文档格式化 | 增加证据选择、压缩、上下文预算与效果对比 |
| Agentic RAG / Query Planning | 第一版完成 | 已有规则复杂度分类、多查询规划、检索合并与重试 | 增加可评测的规则 + LLM 混合任务分析、重排、多源检索和失败类型驱动的重新规划 |
| Structured Memory | 未完成 | 已有基础对话历史 | 增加摘要、重要事实、活跃论文、研究偏好和策略记忆 |
| Tool Governance | 第一版完成 | 已有统一协议、Registry、Router、Executor、只读 Policy、arXiv/OpenAlex Adapter、来源隔离缓存、指标与离线 Benchmark | 增加质量/成本驱动路由、限流、细粒度授权和 MCP Adapter |
| MCP | 未开始 | 无 | 先实现 MCP Client Adapter，后暴露 PaperAgent MCP Server |
| Reflection / Reflexion / Agent Loop | 未完成 | 只有检索分数重试 | 先增加单次任务内反思与分类型修复，再将经过验证的反思写入情节记忆供后续任务复用 |
| 新科研 Skill | 未开始 | 已有 QA、总结、比较、推荐、引用和 PDF 阅读 | 增加实验方案、综述、批判分析和报告生成 |
| 本地知识库与 RAG | 未完成 | `retrieval/vectorstore.py` 尚未形成完整能力 | 建立可插拔解析、切分、Embedding、索引、检索、重排和专项评测体系，通过测试选择技术组合 |
| Multi-Agent | 未开始 | 现有 Skill Router 可作为执行基础 | 增加 Planner、Executor、Reviewer，再逐步分层 |
| 多模态 PDF | 未开始 | 当前主要读取 PDF 文本 | 增加图、表、公式提取与多模态模型分析 |
| Structured Output | 未开始 | API 已使用 Pydantic | 为复杂 Skill 和 Agent 间通信定义输出 Schema |
| Multi-Trajectory / Best-of-N | 未开始 | 无 | 增加候选生成、评分、选择与成本控制 |
| 前端与工程化交付 | 未开始 | 已有 FastAPI / Uvicorn 服务 | 增加前端、Docker、CI/CD 和报告产物管理 |
| Agent 自进化 | 未开始 | 已有指标与离线能力对比基础 | 增加经验库、候选策略实验、批准、灰度和回滚 |

## 阶段依赖关系

```text
当前 PaperAgent
→ 近期稳定性主线
   → 阶段 1：统一 Tool 工具层
      → 阶段 2：多数据源检索与本地知识库
         → 阶段 3：MCP 集成
            → 阶段 4：Verifier / Guardrail / 有限 Agent Loop
               → 阶段 5：Context Engineering / Structured Memory / LLM Wiki
                  → 阶段 6：离线 Agent 自进化
                     → 阶段 7：受控在线适应
→ 科研能力扩展线
   → 阶段 8：科研型 Skill 扩展
      → 阶段 9：Structured Output
         → 阶段 10：轻量 Multi-Agent v1
            → 阶段 11：分层 Multi-Agent
               → 阶段 12：多模态 PDF 理解
                  → 阶段 13：Multi-Trajectory / Best-of-N
→ 产品与交付线
   → 阶段 14：Harness / Verifier / Guardrail 强化
      → 阶段 15：前端展示
         → 阶段 16：Docker 与 CI/CD
```

可观测性、安全、测试、基准评测和回滚能力贯穿全部阶段。

## 跨阶段 Graph Engineering 设计主线

Graph Engineering 不是独立于业务能力的单一阶段，而是贯穿 Tool、RAG、Memory、Agent Loop、Multi-Agent 和 Harness 的横向设计原则。

### 目标图结构

```text
PaperAgent 主图
→ 输入与安全子图
   → 意图判断
   → 输入验证
   → 风险与成本路由
→ 研究规划子图
   → 问题理解
   → 查询改写
   → 查询分解
   → 数据源选择
→ 检索子图
   → 在线工具
   → 可选本地 RAG
   → 可选图检索
   → 结果融合
   → Reranker
→ 推理与生成子图
   → 任务分类
   → Skill 路由
   → 上下文构建
   → 答案生成
→ 验证与恢复子图
   → 检索验证
   → 事实与依据验证
   → 引用验证
   → Reflection
   → 按失败类型选择修复路径
→ 记忆子图
   → 读取相关记忆
   → 生成候选记忆
   → 验证、去重与审批
   → 写入长期记忆
→ 指标与结束节点
```

### 图工程规则

- 主图只负责任务生命周期与子图编排，复杂领域逻辑下沉到职责单一的子图。
- 每个节点必须定义明确的输入字段、输出字段、允许修改的 State 字段、错误类型和幂等性要求。
- 条件边必须有可测试的路由函数，不允许仅依赖难以复现的自由文本判断。
- 每个循环必须具有次数、Token、延迟、工具调用和无提升停止条件。
- 失败类型必须决定恢复路径，检索失败、引用失败、推理失败和工具失败不能统一重复同一动作。
- 始终保留简单任务的短路路径，新增复杂能力不能强制所有请求进入高成本流程。
- Checkpointer 负责工作流暂停、恢复和回放，不与长期记忆混为一体。
- 节点、边、子图、状态 Schema 和停止原因都必须进入 trace 与测试报告。
- 所有新图路线必须提供关闭开关和回滚到上一条稳定路线的能力。

### 图工程专项指标

- 节点和条件边覆盖率；
- 路由准确率与错误分支率；
- 合法路径率与不可达节点数量；
- State 必填字段完整率与跨节点一致性；
- 循环按预算终止率、平均循环次数和无提升停止率；
- 按失败类型统计的恢复成功率；
- Checkpoint 保存、恢复和回放一致率；
- 简单任务短路率及避免的 LLM、工具和 Token 数量；
- 各条图路径的质量、延迟、Token、成本和失败率；
- 候选图相对基线图的能力提升与关键回归数量。

Graph Engineering 的价值不能以节点数量衡量。只有在固定数据集上证明新分支、循环或子图改善质量、可靠性或成本，且没有引入关键回归时，才能进入默认主图。

## 智能任务分析、查询优化与 Skill 路由升级计划

### 当前基线

- `IntentRouter` 使用本地精确规则识别问候、感谢和身份问题，未命中时进入研究流程；简单输入不调用 LLM。
- `QueryRewrite` 使用关键词和固定英文模板改写查询，不调用 LLM。
- `QueryPlan` 使用任务类型和复杂关键词判断简单或复杂任务，再按固定模板生成子查询，不调用 LLM。
- `Reason` 先进行规则任务分类；仅当规则置信度低于阈值时调用 LLM，将结果限制在允许的 `task_type` 枚举内。
- `SkillRouter` 本身不调用 LLM，只根据经过校验的 `task_type` 确定性映射到已有 Skill。
- 当前 `reason` 位于 `retrieve/evaluate` 之后，因此查询规划通常只能依赖原始问题关键词，不能稳定使用正式任务分类结果。

### 升级原则

- 保留规则优先和简单任务短路，不允许为了“智能化”让 `hi`、感谢或明确单一问题强制调用 LLM。
- 仅在规则低置信度、条件复杂、中文长问题、多目标、多约束或需要查询分解时启用 LLM。
- 优先评测一次结构化 `TaskAnalyzer` 调用同时完成任务分类、复杂度分析、查询改写和规划，避免四个节点分别调用 LLM。
- LLM 只生成受 Schema 约束的候选分析；查询数量、长度、权限、成本、枚举和偏题检查由确定性 Validator 控制。
- Skill 选择继续采用“受限任务分类 + 确定性映射”，不允许模型自由选择不存在的 Skill 或直接生成可执行工具名。
- 所有候选能力均保留关闭开关、规则基线和失败回退；只有评测证明净收益后才进入默认流程。

### 候选目标流程

```text
用户问题
→ 高置信度本地意图规则
   ├─ 问候 / 感谢 / 身份问题 → 本地回答并结束
   └─ 研究问题或规则不确定 → Task Analyzer
→ Task Analyzer
   ├─ 简单且规则明确 → 使用规则分析，不调用 LLM
   └─ 含糊或复杂 → 一次 LLM 结构化分析
→ Plan Validator
   → 校验任务类型、复杂度、查询数量、约束、问题偏离和预算
→ 查询计划
   → 原始问题 + 改写查询 + 子查询 + 数据源建议
→ Tool Router / Retrieve / Evaluate
→ 确定性 Skill Router
→ Skill 执行与答案生成
```

### 统一结构化分析结果

候选 `TaskAnalysis` 至少包含：

```json
{
  "intent": "research",
  "task_type": "compare",
  "confidence": 0.91,
  "complexity": "complex",
  "complexity_reasons": ["需要比较两个方法", "包含效果、成本和局限三个维度"],
  "core_topic": "GraphRAG 与 LightRAG",
  "entities": ["GraphRAG", "LightRAG"],
  "constraints": {"domain": "academic research"},
  "rewritten_query": "GraphRAG LightRAG academic research comparison",
  "search_dimensions": ["architecture", "retrieval quality", "cost", "limitations"],
  "sub_queries": [],
  "recommended_query_count": 4
}
```

具体字段和技术实现不得预先写死；应先建立 Pydantic / JSON Schema 和候选接口，再通过测试决定哪些字段能稳定提升检索与回答质量。

### 分模块升级策略

#### 意图判断

- 保留高置信度本地白名单作为零 Token 快速路径。
- 只有规则无法判断时，才允许轻量模型在 `smalltalk`、`paper_research`、`pdf_reading`、`unsupported` 等受限枚举中分类。
- 必须记录短路率、误拦截率、研究问题错误短路数、LLM 调用数和避免的 Token。

#### 查询改写

- 简单专业术语继续使用规则或原查询。
- 中文长问题、多条件、时间范围、方法名、数据集和评价指标等复杂约束可进入 LLM 改写候选。
- 始终保留原始问题，并检查改写结果是否遗漏约束、添加不存在的条件或偏离研究主题。
- LLM 失败、超时、结构校验失败或偏题时回退到规则结果。

#### 复杂度判断与查询规划

- 明确的简单问题保持单查询；明确命中比较、综述、局限和未来方向等规则时可以直接生成有限模板计划。
- 规则冲突或复杂问题允许 LLM 给出复杂度、理由、检索维度和建议查询数量。
- 简单任务和复杂任务都设置查询数量硬上限、去重、长度限制、工具调用预算和提前停止条件。
- 评测当前图与“任务分析提前到查询规划之前”的候选图，依据数据决定是否调整 `reason` 节点位置或拆分轻量 `TaskAnalyzer` 子图。

#### Skill 选择

- 规则高置信度时直接得到 `task_type`；低置信度时由 LLM 在允许枚举中辅助分类。
- 分类结果经过 Schema 和白名单校验后，再由本地 `SkillRouter` 确定性映射到 QA、总结、比较、推荐、引用、PDF 阅读及未来科研 Skill。
- 无效分类、低置信度或不存在的 Skill 一律回退到 `QASkill` 或进入明确的澄清路径。
- 后续即使增加 Multi-Agent，也必须先由复杂度门控决定是否升级执行模式，普通任务继续走单 Agent + Skill 路径。

### 专项评测与晋升门槛

至少建立以下对照组：

```text
A：当前纯规则改写与规划基线
B：各节点分别使用 LLM
C：一次结构化 Task Analyzer + 确定性 Validator
D：规则优先、低置信度才调用 Task Analyzer 的混合方案
```

评测至少包含：

- 意图准确率、研究问题误短路率和简单任务短路率；
- `task_type` 与 Skill 路由准确率；
- 复杂度准确率、查询计划有效率、约束保留率和查询偏题率；
- Recall@K、MRR、nDCG@K、结果覆盖维度和重复论文比例；
- 最终答案正确性、完整性、Faithfulness 和引用有效率；
- 每个请求的 LLM 调用数、Token、成本、P50/P95 延迟和工具调用数；
- LLM 失败、超时、非法结构和规则回退成功率；
- 不同语言、短问句、长问题、多实体、多约束和对抗性输入的鲁棒性。

候选方案只有在研究问题误短路不增加、关键质量指标达到门槛、简单任务成本没有明显回归，并且单位质量提升对应的 Token 与延迟可接受时，才能晋升为默认路径。测试用例、指标定义和每次结果继续写入中文文档、Benchmark 与 Excel 报告。

## 阶段 1：统一 Tool 工具层

### 目标

在增加更多数据源或 MCP Server 前，将 LangGraph 节点与具体 API 解耦，建立一套可审计的工具执行协议。

### 当前完成情况（2026-08-05）

- 已实现 `ToolSpec`、`RetryPolicy`、`ToolResult` 和统一错误码；
- 已实现 `ToolRegistry`、确定性 `ToolRouter` 和 `ToolExecutor`；
- 已实现默认只允许只读工具的 `ToolPolicy`，未授权写工具在执行前被拒绝；
- 已使用 Pydantic 对工具输入和输出进行双向校验；
- 已实现有限超时、有限重试、错误标准化、来源、版本、风险和延迟记录；
- 已将原有 arXiv 函数包装为 `paper.search.arxiv` Native Adapter；
- `retrieve_node` 已通过 Router 与 Executor 调用 arXiv，并保留原有缓存与 fallback 行为；
- Metrics 已汇总工具成功、失败、耗时和执行明细；
- 已增加单元、检索集成、测试说明和离线基线/候选 Benchmark。

第一版离线 Tool Benchmark：执行准确率 `16.67% → 100%`，非法输入、非法输出、未授权写工具和执行错误均被结构化处理，并能通过有限重试恢复一次临时失败。

### 计划组件

- `ToolSpec`：稳定名称、说明、版本、能力、风险等级、输入结构、输出结构、超时、重试与缓存策略。
- `ToolResult`：成功状态、标准化结果、来源、延迟、错误码、缓存状态、原始结果数量与执行元数据。
- `ToolRegistry`：注册和发现原生工具及 MCP 工具。
- `ToolExecutor`：校验输入、执行超时/重试/限流、调用工具、标准化错误并记录指标。
- `ToolRouter`：按照任务类型、领域、查询复杂度、数据源可用性和成本策略选择最少且足够的工具。
- `NativeToolAdapter`：包装现有 arXiv 实现，同时保持当前检索行为不变。

### 安全规则

- 策略允许时，只读工具可以自动运行。
- 写入数据、执行代码或披露用户内容的工具必须具有明确风险等级，必要时要求人工批准。
- 工具输出在完成校验和标准化前一律视为不可信数据。
- 存在安全兜底方案时，单个工具失败不得导致整个图崩溃。

### 验收门槛

- 现有 arXiv 行为不变，当前测试全部通过。
- `retrieve_node` 不再直接导入某个具体搜索服务。
- 每次工具调用都记录来源、耗时、成功状态、错误和缓存状态。
- 无效参数、超时、限流、工具不可用和兜底路径均有测试。
- 简单问题的外部工具调用数量不增加。

## 阶段 2：多数据源检索与本地知识库

### 目标

提高论文覆盖率、正式出版元数据质量和引用关系发现能力，同时避免每个查询都调用所有数据源。

### 计划数据源

- arXiv：近期预印本与开放论文元数据。
- OpenAlex：论文、作者、期刊会议、机构、引用和撤稿信息。
- Semantic Scholar：相关论文、引用网络与研究发现。
- Crossref：DOI 和正式出版元数据核验。
- PubMed：可选的医学与生命科学专业数据源。
- 本地 PDF 与未来的本地向量索引：用户拥有的论文内容。

### 当前已完成的多源基础

- OpenAlex Works API 原生 Client 与 `paper.search.openalex` 只读 Adapter；
- OpenAlex 作者、倒排摘要、DOI、开放获取链接、引用次数和平台 ID 到统一论文结构的转换；
- `arxiv`、`openalex`、`multi` 三种配置模式，默认 `arxiv` 基线不变；
- arXiv 与 OpenAlex 独立缓存命名空间；
- 多源合并采用 DOI、平台 ID、PDF URL、标题的稳定去重优先级；
- 单一来源失败时保留其他来源成功结果，所有来源无结果时才进入静态 fallback；
- 离线 Benchmark 覆盖互补结果、跨源 DOI 重复和部分来源失败三个场景。

当前完成的是“可运行、可关闭、可观测”的多源工程基础，不代表 OpenAlex 已经通过真实质量选型。下一门槛是固定标注问题集上的在线对照评测。

OpenAlex 真实在线运行建议配置免费的 `OPENALEX_API_KEY`。无密钥请求额度较低，额度耗尽时 Client 会将 HTTP 429 转换为 `RATE_LIMITED`，由 Tool Executor 执行有限重试并保留结构化失败；多源模式仍可继续使用其他成功来源。

### 本地论文知识库

本地知识库作为后续正式能力建设，但不提前写死解析器、Embedding、向量库、检索算法、Reranker 或图检索实现。计划先建立统一接口和评测基线，再用项目自己的论文数据与问题集选择技术组合。

计划建立完整的本地检索链路：

```text
PDF
→ 文本与元数据提取
→ Chunker 分块
→ Embedding
→ 写入可替换的向量存储
→ Dense / Sparse / Hybrid 候选检索
→ 可选 Reranker
→ 与在线论文结果合并、去重和重排
```

计划抽象以下可插拔接口：

- `DocumentParser`：PDF、版面、表格、公式与元数据解析；
- `Chunker`：固定长度、递归、章节感知、Parent-Child 或其他切分策略；
- `EmbeddingProvider`：本地模型或在线 Embedding API；
- `VectorStore`：ChromaDB、Qdrant、FAISS 或后续新增实现；
- `Retriever`：Dense、Sparse / BM25、Hybrid、在线与本地融合；
- `Reranker`：无重排、本地 CrossEncoder、在线服务或 LLM 重排；
- `GraphRetriever`：关闭、LightRAG、GraphRAG 或自定义论文关系检索。

LangGraph 和业务节点只能依赖上述稳定接口，不得直接绑定具体产品。ChromaDB、Qdrant、BGE、Docling、LightRAG 和 GraphRAG 等名称只作为候选方案，不代表最终选型。

建议目录：

```text
rag/
├─ interfaces.py
├─ registry.py
├─ pipeline.py
├─ configs/
├─ parsers/
├─ chunkers/
├─ embeddings/
├─ stores/
├─ retrievers/
├─ rerankers/
└─ graph_retrievers/
```

同时增加本地索引版本、文档哈希、幂等写入、增量更新、删除、重建、来源追踪和数据隔离机制。

### RAG 技术选型与专项评测

RAG 选型由配置驱动的对照实验决定。每个实验必须记录：

- Parser、Chunker、Embedding、VectorStore、Retriever、Reranker 和 GraphRetriever 的名称与版本；
- `chunk_size`、`chunk_overlap`、`top_k`、`rerank_top_k`、相似度阈值、融合算法和元数据过滤条件；
- 数据集、Prompt、模型、代码 Commit、随机种子和评估器版本；
- 质量、延迟、资源、Token、API 调用和成本结果。

RAG 测试集至少覆盖：

- 精确事实、方法细节、实验数值和论文结论；
- 跨章节与跨论文比较；
- 页码、章节和证据片段定位；
- 论文标题、作者、缩写、方法名和数据集等关键词查询；
- 中文提问与英文论文的跨语言检索；
- 知识库无答案、相似干扰文档和过期版本；
- 需要在线最新论文、本地全文或在线与本地联合检索的不同任务。

每个标注用例应包含问题、参考答案、相关论文、相关页码或章节、标准证据片段、问题类别、难度和是否需要跨文档推理。

评测指标分为三类：

- 检索质量：Hit Rate@K、Recall@K、Precision@K、MRR、nDCG@K、Context Precision 和 Context Recall；
- 答案质量：正确性、完整性、Faithfulness、Citation Correctness、Citation Coverage 和无答案拒答准确率；
- 工程表现：检索延迟、总响应时间、索引时间、存储占用、内存/显存、Token、单次成本和多次运行稳定性。

不以单个总分决定选型。先设置质量、引用和安全门槛，再在达标方案中比较延迟、成本、资源占用和维护复杂度。允许同时保留快速、标准和深度研究等不同运行档位。

实验按控制变量逐步推进，避免一次性组合爆炸：

```text
当前 arXiv 检索基线
→ 本地 Dense 检索基线
→ Embedding 对比
→ Chunking 对比
→ VectorStore 等价能力与工程表现对比
→ Dense 与 Hybrid 对比
→ 无 Reranker 与不同 Reranker 对比
→ 在线、本地及联合检索对比
→ 普通 RAG 与 LightRAG / GraphRAG 候选对比
→ 接入 LangGraph 后的端到端回归评测
```

图检索不作为本地知识库第一版的前置条件。只有普通 RAG 基线稳定，并且关系型、跨论文或全局主题问题的测试证明图检索带来稳定收益时，才晋升 LightRAG、GraphRAG 或自定义图检索方案。
- 本地索引版本、文档哈希、删除、重建和数据隔离机制。

### 路由策略

```text
近期预印本请求 → arXiv
相关论文或引用网络请求 → OpenAlex / Semantic Scholar
DOI 或出版信息核验 → Crossref
医学问题 → PubMed
上传文档请求 → 本地 PDF / 本地索引
广泛比较或综述 → 选择必要数据源并行检索 → 标准化 → 去重 → 重排
```

### 验收门槛

- 所有数据源返回统一的 `PaperDocument` 模型。
- 跨源去重依次使用 DOI、arXiv ID、数据源 ID 和标准化标题。
- 数据来源信息在结果合并和最终答案生成后仍能保留。
- 多源检索提升已标注数据集的覆盖率或召回率，同时不超过约定的延迟与工具调用预算。
- 单个数据源失败不会删除其他数据源返回的有效结果。
- 本地论文索引支持可重复构建、增量更新、删除和来源追踪。
- 所有 RAG 组件可通过配置和 Registry 替换，LangGraph 主流程不依赖具体供应商实现。
- 至少建立关键词/在线检索、Dense、本地 Hybrid 和可选 Reranker 的基线/候选对照。
- 最终采用或淘汰某项技术必须有固定测试集、指标和工程成本数据支持。
- Embedding 模型或向量维度变化时具有明确的索引版本与重建策略。

## 阶段 3：MCP 集成

### 目标

通过 MCP 组合外部能力，同时保持 LangGraph 业务逻辑不依赖具体传输方式和服务提供者。

### 优先实现 MCP Client

- 在统一的 `ToolSpec` 和 `ToolResult` 接口后增加 `MCPToolAdapter`。
- 支持工具发现、结构校验、调用、取消、超时和错误处理。
- 首先只连接一个可信、只读的 MCP Server。
- 维护 Server 与 Tool 白名单，不自动信任外部工具说明。
- 记录 MCP Server 身份、工具版本、调用参数、结果状态和耗时。

### 后续实现 MCP Server

PaperAgent 能力稳定后，将以下只读能力逐步暴露为 MCP 工具：

- `paper.search`
- `paper.get_metadata`
- `paper.read_pdf`
- `paper.summarize`
- `paper.compare`
- `paper.find_related`
- `paper.trace_citations`
- `paper.recommend_directions`

### MCP 能力映射

- Tools：主动搜索、元数据查询、引用关系遍历和论文分析。
- Resources：审核后的 LLM Wiki、本地论文库和只读项目知识。
- Prompts：可选的、由用户主动选择的文献综述或论文比较模板。

### 验收门槛

- 原生工具和 MCP 工具通过同一套工具协议测试。
- 不可信或未授权的 MCP 工具无法执行。
- Server 断连、结构不匹配、超时、部分结果和取消均有测试。
- MCP 集成不改变下游节点使用的标准化文档结构。

## 阶段 4：Verifier、Guardrail、Reflection 与有限 Agent Loop

### 目标

让 Agent 能够通过少量、可观测的循环修正较差检索或答案，而不是重复同一动作或无限运行。

### Verifier 与 Guardrail

现有 `validators/` 将继续扩展，并正式接入最终答案流程：

- Answer Verifier：答案是否为空、是否回答用户问题、结构是否完整。
- Citation Verifier：引用格式、论文身份和元数据是否一致。
- PDF Grounding Verifier：PDF 任务是否以 `pdf_text` 为依据。
- Retrieval Verifier：检索来源、缓存状态、分数和结果数量是否一致。
- Hallucination Guardrail：是否编造不存在的论文、作者、DOI 或实验结论。
- Latency / Budget Guardrail：节点耗时、Token 和工具调用是否超过预算。

Verifier 负责给出可解释检查结果，Guardrail 负责执行允许、修复、拒绝或人工审核策略，Reflection 根据失败类型生成下一轮改进计划。

### Reflection 与 Reflexion 的职责边界

项目同时保留两个概念，但必须分阶段实现：

```text
Reflection
→ 发生在当前任务内部
→ 根据本轮检索、工具、答案和 Verifier 反馈生成结构化批评
→ 决定当前任务下一轮如何修复
→ 默认不跨任务长期保存

Reflexion
→ 发生在一次尝试或任务结束之后
→ 将外部或内部反馈转化为简短的语言经验
→ 经过验证、去重、版本化和必要的人工批准后写入情节记忆
→ 在未来相似任务中检索并影响新的决策
```

Reflexion 不更新模型权重，属于通过语言反馈和情节记忆实现的跨尝试改进机制。项目第一版只实现 Reflection；只有 Reflection 的反馈质量、恢复收益和成本经过固定数据集验证后，才启用跨任务 Reflexion。

### Reflection 第一版

Reflection 输出使用结构化 Schema，至少包含：

- `failure_type`：检索不足、来源失败、证据不足、引用错误、答案偏题、格式错误、预算超限或未知；
- `evidence`：支持该判断的节点结果、Validator 错误和指标；
- `critique`：本轮失败或低质量的具体原因；
- `improvement_plan`：下一轮允许采取的有限动作；
- `expected_gain`：预期改善的指标；
- `risk`：额外 Token、延迟、工具调用或引入噪声的风险；
- `stop_recommendation`：继续、返回最佳答案、拒答或请求人工确认。

Reflection 不能直接修改代码、安全策略、Benchmark 标签或长期记忆，只能从预先允许的修复动作中选择。

### Reflexion 后续版本

```text
任务轨迹与反馈
→ 生成候选语言反思
→ Verifier 校验事实与失败类型
→ 与历史反思去重和冲突检查
→ 离线回放验证是否改善相似任务
→ 必要时人工批准
→ 写入 Episodic / Strategy Memory
→ 后续相似任务按相关性、置信度和时效检索
→ 监控复用后的质量、成本和回归
→ 保留、修订、隔离、过期或回滚
```

长期保存的反思必须记录来源轨迹、反馈信号、适用任务、验证数据集、质量增益、成本变化、置信度、版本、状态和过期策略。未经验证的自我评价只能保留为候选记录，不能成为生效策略。

### 计划流程

```text
用户问题
→ 意图路由
→ 检索相关历史经验
→ 查询改写与规划
→ 论文检索
→ 检索质量评估
   ├─ 证据不足 → 生成批评 → 重新规划/检索
   └─ 证据充分 → 推理 → 生成答案
→ 最终答案评估
   ├─ 引用问题 → 修复引用 → 重新生成
   ├─ 推理问题 → 反思 → 重新推理/生成
   ├─ 证据问题 → 反思 → 重新规划/检索
   ├─ 达到质量阈值 → 结束
   └─ 达到次数/Token/时间预算 → 返回最佳答案并记录停止原因
```

### 计划增加的 State 字段

- `loop_iteration`
- `max_loop_iterations`
- `answer_scores`
- `failure_type`
- `critique`
- `improvement_plan`
- `feedback_signal`
- `reflection_candidate`
- `retrieved_reflection_ids`
- `best_answer`
- `best_score`
- `stop_reason`
- `loop_token_budget`

### 初始限制

- 最多修正 2 轮。
- 达到质量阈值后立即停止。
- 连续两轮没有明显质量提升时停止。
- Token、延迟或外部工具调用预算耗尽时停止。
- 始终保留并返回得分最高的有效答案，而不是默认返回最后一轮答案。

### 持久化

- 使用 checkpointer 编译 LangGraph。
- 为可恢复会话使用稳定的 `thread_id`。
- 保存检查点，以支持调试、回放、人工审核和替代路径实验。
- 增加中断与恢复前，保证所有带副作用操作具有幂等性。

### 验收门槛

- 所有循环路径都有严格的次数和资源上限。
- 失败类型决定恢复路径，检索失败不能只触发答案重写。
- 固定数据集上的 `success_at_n` 高于 `success_at_1`。
- 报告质量提升时必须同时报告额外 Token、延迟和工具调用。
- 保留关闭 Loop 的模式，作为基线和回滚路径。
- Writer/Generate 的输出必须先经过 Verifier 与 Guardrail，才能晋升为最终答案。
- 每种验证失败都具有明确错误码、修复路径和测试案例。
- Reflection 相对“无反思重试”基线必须提高恢复成功率，且报告额外 Token、延迟和工具调用。
- 关闭 Reflection 与 Reflexion 时，系统必须能够运行原始稳定图，作为基线和回滚路径。
- Reflexion 记忆写入必须经过验证门控，错误、矛盾、过期或无收益反思可以隔离和回滚。
- 评测必须区分“当前任务内 Reflection 带来的提升”和“跨任务 Reflexion 记忆复用带来的提升”。

## 阶段 5：Context Engineering、Structured Memory 与 LLM Wiki

### 目标

将经过验证的结果转化为可复用经验，同时禁止未经验证的模型输出直接成为永久策略或事实知识。

### Context Engineering

不同任务不能继续把 history、documents、pdf_text 和 metadata 全部直接拼入 Prompt。计划由 Context Builder 统一完成选择、压缩、排序和预算控制：

```text
原始状态
→ 任务识别
→ Evidence Selector 选择相关证据
→ Document Compressor 压缩冗余内容
→ Context Policy 应用任务规则与 Token 预算
→ Context Builder 生成最终上下文
```

任务差异示例：

- CitationSkill：标题、作者、年份、DOI、URL 与来源标识。
- PaperSummarySkill：摘要、方法、贡献与结论。
- ResearchDirectionSkill：方法、不足、实验结论和趋势。
- PDFReadingSkill：相关 PDF 片段、会话摘要和当前问题。
- LiteratureReviewSkill：主题分类、代表论文、方法对比与引用信息。

需要增加证据覆盖率、压缩率、上下文 Token、答案质量变化和无关证据比例等指标。

### 记忆层级

- 情节记忆：任务、执行轨迹、反馈、分数变化和最终结果。
- 策略记忆：经过批准的成功查询方案与失败恢复规则。
- 知识记忆 / LLM Wiki：经过审核的能力说明、研究方法、数据源指导和可复用知识。
- 对话记忆：具有明确保留规则和隐私规则的用户上下文。

### 存储分层与 Redis 候选方案

逻辑记忆分层不要求所有数据存入同一种数据库。不同数据按照持久性、查询方式、并发和恢复要求选择存储，并通过统一接口隔离具体实现：

```text
文件系统
→ 原始 PDF、解析产物、Benchmark 数据、Excel 报告和 LLM Wiki 文档

关系数据库候选（第一版本地可使用 SQLite）
→ 完整会话、会话摘要、用户研究画像、结构化记忆、任务轨迹、经验审批、版本和回滚记录

可替换向量存储
→ 论文正文、对话摘要和任务经验的语义索引

Redis 候选缓存层
→ 热点会话、检索结果、Embedding、LLM 响应、限流计数、分布式锁和长任务进度

LangGraph Checkpointer
→ 单次工作流的暂停、恢复和回放状态
```

Redis 不作为长期记忆、论文知识、Benchmark 或策略经验的唯一事实来源。即使启用 Redis 持久化，也必须明确 TTL、淘汰、恢复和数据丢失策略。长期数据由关系数据库、文件系统或其他经过评测的持久存储承担。

计划抽象统一缓存接口，例如：

```text
CacheBackend
├─ InMemoryCache
├─ FileCache
├─ SQLiteCache
└─ RedisCache
```

业务节点只依赖 `get`、`set`、`delete`、TTL 和必要的锁语义，不直接依赖 Redis 客户端。当前单用户、单进程、本地运行阶段优先保持简单；出现多 Uvicorn Worker、多 Agent 进程、统一限流、后台长任务、实时进度或 JSON 并发竞争后，再将 Redis 作为重点候选进行评测。

推荐演进顺序：

```text
当前 JSON 文件记忆与文件缓存
→ 统一 MemoryStore / CacheBackend 接口
→ SQLite 作为本地默认持久实现
→ Redis 作为可选热缓存与分布式状态实现
→ 多进程或部署阶段通过评测决定是否默认启用
```

Redis 候选评测至少包含缓存命中率、P50/P95 延迟、并发正确率、TTL 与淘汰行为、重启后表现、故障降级、内存占用和部署维护成本。

### Structured Memory 数据

- 会话摘要；
- 重要事实；
- 当前活跃论文及其活跃原因；
- 用户研究主题、方法偏好和实验偏好；
- 已确认的论文关系与研究问题；
- 记忆来源、置信度、创建时间、过期时间和删除状态。

### 经验记录内容

- 任务类型与查询特征。
- 失败类型与批评。
- 使用的改进策略。
- 改进前后分数。
- Token、延迟和工具调用变化。
- 支持该经验的执行轨迹或 Benchmark 案例。
- 置信度、状态、版本、批准和过期信息。
- Reflection / Reflexion 的反馈来源、候选文本、适用边界、复用次数和复用后的实际质量变化。

### 经验晋升流程

```text
原始执行轨迹
→ 候选经验
→ 去重与校验
→ 离线回放
→ 必要时人工批准
→ 正式策略 / LLM Wiki 条目
→ 监控复用效果
→ 保留、修订、隔离、过期或回滚
```

### 验收门槛

- 原始失败记录和单次成功不能直接修改生效策略。
- 每条生效策略都具有来源、证据、版本和回滚信息。
- 记忆检索按照任务类型与置信度过滤，并有上下文和 Token 预算。
- 可以隔离被污染、过期、矛盾或低置信度的记忆。
- 除非通过批准流程，否则运行时 Agent 对 Wiki 只有读取权限。
- 会话、结构化记忆、语义记忆、缓存和 Checkpointer 具有独立接口与命名空间，不能混为同一类状态。
- Redis 不可用时，核心单机流程能够降级到本地持久存储或绕过缓存继续运行。
- 缓存写入、命中、失效、TTL、并发、故障和敏感数据处理都有测试与指标。
- 用户能够查询、删除或使其会话与长期记忆过期，删除操作应同步清理相关缓存与语义索引。

## 阶段 6：离线 Agent 自进化

### 目标

通过离线、可测量的实验改进提示词、路由规则、检索策略和策略记忆，避免失控的生产环境自我修改。

### 进化循环

```text
历史轨迹与 Benchmark 失败案例
→ 聚类失败模式
→ 提出 Prompt / 路由 / 策略候选
→ 在固定数据集上运行候选版本
→ 比较质量、回归、成本和延迟
→ 拒绝或请求批准
→ 版本化晋升
→ 灰度或影子评估
→ 持续监控并在需要时回滚
```

### 初期允许进化的部分

- 查询改写提示词和规则。
- 各任务类型的查询规划模板。
- 数据源选择策略。
- 检索阈值与重试路由。
- 推理、生成、答案评估和反思提示词。
- Skill 选择规则与经过批准的策略记忆。

### 初期禁止自动修改的部分

- 生产 Python 代码。
- 安全与授权策略。
- Benchmark 标签和参考答案。
- 用于批准候选版本的评估阈值本身。
- 密钥、外部凭证和用户隐私策略。

### 验收门槛

- 所有候选版本使用相同的基线数据集和评估器版本。
- 晋升要求没有关键回归，并达到预先定义的最低质量提升。
- 质量提升报告必须包含成本与延迟变化。
- 记录 Prompt、策略、工具、模型、数据集和评估器版本。
- 每次晋升都可以一步回滚。

## 阶段 7：受控在线适应

### 目标

利用生产反馈提出改进方案，同时保持部署决策受控。

### 计划控制措施

- 评估前对生产轨迹进行抽样和脱敏。
- 组合使用代码校验器、参考答案检查、LLM Judge 和人工反馈。
- 将失败或低置信度轨迹加入离线数据集。
- 候选版本进入灰度前先以影子模式运行。
- 涉及安全、隐私、写操作或外部通信的变化必须人工批准。
- 回归或预算指标超过阈值时自动停用候选版本。

## 阶段 8：科研型 Skill 扩展

### 目标

在现有问答、总结、比较、推荐、引用和 PDF 阅读能力上，补齐从论文理解到科研选题、实验设计和报告写作的完整链路。

### ExperimentIdeaSkill

根据论文或研究方向生成可实施的实验方案，输出应包含：

1. 实验目标；
2. Baseline 方法；
3. 改进思路；
4. 数据集选择；
5. 评价指标；
6. 实验步骤；
7. 对比实验；
8. 消融实验；
9. 预期结果；
10. 风险与难点。

建议文件：`skills/experiment_idea_skill.py`。

### LiteratureReviewSkill

根据多篇论文生成结构化文献综述，输出应包含研究背景、技术发展脉络、方法分类、代表性论文、方法对比、当前不足、未来趋势和参考文献。

建议文件：`skills/literature_review_skill.py`。

### PaperCritiqueSkill

分析论文的方法假设、实验不足、数据集局限、泛化问题、研究空白和可改进方向。

建议文件：`skills/paper_critique_skill.py`。

### ReportWritingSkill

将论文总结、方法比较、研究空白、实验设计和引用整合为完整研究报告，支持开题报告、课程报告和研究选题报告。

建议文件：`skills/report_writing_skill.py`。

### 能力链路

```text
阅读论文
→ 总结与比较
→ 批判分析
→ 发现研究空白
→ 推荐研究方向
→ 设计实验
→ 生成文献综述或完整报告
```

### 验收门槛

- 每个 Skill 都有明确输入、结构化输出、证据要求和验证器。
- 引用和事实结论可以追溯到论文来源。
- 实验方案必须包含可执行步骤、Baseline、指标和风险，而不是只有泛化建议。
- 新 Skill 必须加入路由测试、生成质量评测和 Excel 测试说明。

## 阶段 9：Structured Output 结构化输出

### 目标

让复杂 Skill 和 Agent 之间使用明确的数据结构通信，再由 Formatter 转换为 API、前端或报告格式。

### 优先适用能力

- ExperimentIdeaSkill；
- LiteratureReviewSkill；
- PaperCritiqueSkill；
- ReportWritingSkill；
- Multi-Agent 中间计划和最终报告；
- Verifier、Reflection 和 Reviewer 的评分结果。

示例：

```json
{
  "experiment_goal": "",
  "baselines": [],
  "datasets": [],
  "metrics": [],
  "steps": [],
  "risks": []
}
```

### 验收门槛

- 使用 Pydantic / JSON Schema 校验模型输出。
- 结构校验失败时具有有限修复次数和明确错误码。
- API Schema、AgentState 和前端字段含义保持一致。
- Harness 可以直接校验必填字段、枚举、引用和跨字段一致性。

## 阶段 10：轻量 Multi-Agent v1

### 目标

不推翻现有单 Agent + Skill Router 架构，只让复杂科研任务进入轻量 Multi-Agent Orchestrator。

### 第一版角色

- PlannerAgent：理解复杂请求并拆解任务步骤。
- ExecutorAgent：按照计划调用现有工具、检索流程和 Skill。
- ReviewerAgent：检查完整性、问题偏离、证据、引用和格式。

建议目录：

```text
multi_agent/
├─ orchestrator.py
├─ planner_agent.py
├─ executor_agent.py
└─ reviewer_agent.py
```

### 路由原则

```text
普通问答 / 单篇总结 / BibTeX / 简单比较
→ 继续使用单 Agent + Skill Router

完整研究课题 / 综述 + 空白 + 实验 + 引用 / 研究报告
→ Task Complexity Router
→ MultiAgentOrchestrator
→ PlannerAgent
→ ExecutorAgent
→ ReviewerAgent
→ 最终答案
```

### 验收门槛

- 复杂度路由准确率达到预设阈值，简单任务不会误用 Multi-Agent。
- 计划步骤、Agent 交接数据和工具调用全部可追踪。
- Reviewer 不能无限要求重写，必须受 Loop 和预算控制。
- 与单 Agent 基线比较质量、Token、延迟和失败率。

## 阶段 11：Hierarchical Multi-Agent 分层多 Agent

### 目标

在轻量 Multi-Agent 经过数据验证后，再升级为分层专家协作。

### 计划角色

- ManagerAgent：整体任务规划、预算和调度。
- RetrieverAgent：论文检索和多源数据获取。
- ReaderAgent：论文阅读、PDF 分析和摘要。
- CriticAgent：发现方法不足和研究空白。
- ExperimentAgent：生成并检查实验方案。
- CitationAgent：核验和生成引用。
- WriterAgent：整合结构化研究报告。
- ReviewerAgent：执行最终质量检查和有限修正。

### 验收门槛

- 只有能够证明专家拆分优于轻量 Multi-Agent 的任务才启用分层模式。
- Agent 间通信使用结构化 Schema，而不是自由文本堆叠。
- Manager 负责预算和停止条件，子 Agent 不能自行无限创建 Agent。
- 每个角色都具有独立质量指标、失败路径和回滚到轻量模式的开关。

## 阶段 12：多模态 PDF 理解

### 目标

让系统不仅能读取 PDF 文本，还能理解论文中的图、表、公式、流程图和实验结果。

### 计划能力

- FigureUnderstandingSkill：解释模型结构图、流程图和示意图。
- TableAnalysisSkill：读取并比较实验结果表格。
- FormulaExplanationSkill：解释公式、损失函数、符号和变量。
- MultimodalPDFSkill：综合文本、图像、表格和公式回答问题。

建议增加：

```text
document_loader/
├─ figure_extractor.py
├─ table_extractor.py
└─ formula_extractor.py

skills/
├─ figure_understanding_skill.py
├─ table_analysis_skill.py
├─ formula_explanation_skill.py
└─ multimodal_pdf_skill.py
```

### 第一版实现

```text
PDF
→ 页面与版面解析
→ 指定页渲染为图像
→ 提取候选图、表和公式区域
→ 多模态模型生成结构化描述
→ 与相关 PDF 文本共同进入 Context Builder
→ MultimodalPDFSkill
→ 带页码和区域来源的答案
```

### 验收门槛

- 所有图、表、公式描述保留页码、区域和源文件信息。
- 表格数值抽取、公式符号解释和图像描述分别建立测试集。
- 多模态结果必须与附近文本交叉验证，不能仅依赖图片猜测。
- 报告图像 Token、处理时间、抽取成功率和答案质量增益。

## 阶段 13：Multi-Trajectory / Best-of-N

### 目标

为少量高价值复杂任务生成多个候选方案，由 Verifier 或 Reviewer 选择最佳结果。

### 适用任务

- 研究方向推荐；
- 文献综述；
- 实验方案；
- 研究报告；
- 复杂 Multi-Agent 报告。

### 流程

```text
生成候选 A / B / C
→ 使用同一证据集和结构化评分标准
→ Verifier / Reviewer 独立评分
→ 选择最佳有效候选
→ 必要时合并互补内容
```

### 验收门槛

- 默认关闭，仅对高价值复杂任务或显式请求启用。
- 候选数量、并发、Token 和时间都有上限。
- 评分器版本与候选生成器版本分离并被记录。
- Best-of-N 相对单候选必须有稳定质量收益，否则不晋升。

## 阶段 14：Harness、Verifier 与 Guardrail 强化

### 目标

把当前确定性离线 Benchmark 扩展为覆盖服务、图轨迹、模型质量、工具、MCP、多模态和 Multi-Agent 的完整驾驭工程体系。

### 计划评测层级

- 单元测试：函数、节点、工具协议与结构模型。
- 图集成测试：节点顺序、条件路由、Loop、检查点和恢复。
- 服务测试：FastAPI Schema、错误码、trace_id 和状态隔离。
- 离线能力 Benchmark：固定数据集上的基线/候选对比。
- 在线抽样评测：真实模型、真实工具与真实延迟成本。
- 回归数据集：历史失败案例和用户批准的代表任务。

### 重点验证内容

- Skill Router 与 Tool Router 是否选择正确。
- Cache、Memory、本地知识库、PDF 和 MCP 是否正常。
- Answer、Citation、PDF Grounding、Retrieval 和 Structured Output 是否有效。
- Multi-Agent 轨迹是否完整且未越权。
- Loop 是否按预算停止并返回最佳答案。
- 新版本是否提高质量且没有关键回归。
- 不同 Parser、Chunker、Embedding、VectorStore、Retriever、Reranker 和 GraphRetriever 组合的检索质量与工程成本。
- RAG 测试用例中的标准论文、页码、章节和证据片段是否被正确召回。
- 主图与子图的节点顺序、条件边、状态字段、短路、循环停止、失败恢复和检查点是否符合设计契约。

### 验收门槛

- 每次行为变更都生成基线/候选对比和测试表格。
- 失败案例自动进入待审核回归集，而不是直接进入训练或策略记忆。
- CI 中运行确定性、无网络、无 API 成本的测试；在线评测独立执行。
- 报告包含 Commit、配置、模型、Prompt、工具、数据集和评估器版本。
- RAG 评测支持配置矩阵、单变量对照、保留测试集和历史趋势比较。
- 自动评测不能只依赖 LLM Judge；关键检索标签、引用和代表性答案需要人工标注或规则校验。

## 阶段 15：前端展示

### 目标

为项目增加便于个人使用、演示和调试的可视化界面。

第一版可以使用 Streamlit，后续再根据需要升级前端技术栈。

计划展示：

- 问题输入与 PDF 上传；
- 论文卡片、来源、DOI、引用与相关论文；
- 最终答案及证据定位；
- metrics、Token、延迟、cache_hit 和 trace_id；
- conversation_id、PDF 页数和活跃论文；
- Agent Loop、工具调用和 Multi-Agent 执行步骤；
- Harness 测试结果与版本对比。

### 验收门槛

- 前端只通过稳定 API 调用后端，不直接导入业务节点。
- 长任务支持进度展示、取消和错误恢复。
- 敏感配置、内部 Prompt 和未经授权的工具参数不暴露给前端。

## 阶段 16：Docker 与 CI/CD

### 目标

完成可重复部署、自动化测试和报告产物管理。

计划增加：

- `Dockerfile`
- `docker-compose.yml`
- `.github/workflows/test.yml`
- `.github/workflows/eval.yml`

### CI/CD 流程

```text
Push / Pull Request
→ 安装锁定依赖
→ 静态检查与单元测试
→ 图和服务集成测试
→ 离线 eval_harness
→ 生成测试与能力报告
→ 检查回归门槛
→ 构建镜像
→ 人工批准后部署
```

### 验收门槛

- 环境、依赖和配置可重复构建。
- 测试失败或关键回归时禁止发布。
- 密钥不写入镜像、日志或报告。
- 测试报告、Benchmark 和镜像都能追溯到同一 Git Commit。

## 最终项目分层

```text
1. API 接入层
   FastAPI、Pydantic Schema、统一错误处理
→ 2. Service 编排层
   PaperAgentService、状态初始化、Memory、PDF Loader
→ 3. Context Engineering 与 Memory 层
   Context Builder、Evidence Selector、Compressor、Structured Memory、LLM Wiki
→ 4. LangGraph 工作流层
   主图、领域子图、Intent、Rewrite、Plan、Retrieve、Evaluate、Reason、Generate、Reflect、Metrics
→ 5. Tool、MCP 与数据层
   Tool Registry、Executor、Policy、arXiv、多源 API、MCP、本地知识库
→ 6. Skill 能力层
   QA、总结、比较、推荐、引用、PDF、实验、综述、批判、报告、多模态
→ 7. Multi-Agent 协作层
   Planner、Executor、Reviewer 与分层专家 Agent
→ 8. 工程观测与质量控制层
   trace_id、日志、指标、Verifier、Guardrail、检查点与回滚
→ 9. Harness 驾驭工程层
   案例、Runner、Validator、报告、回归集和 CI
```

## 跨阶段评测指标

### 质量指标

- 意图、查询规划、结果合并、重试和工具路由准确率。
- 检索 Hit Rate@K、Recall@K、Precision@K、MRR、nDCG@K、Context Precision、Context Recall 与数据源覆盖率。
- 引用有效率、引用完整率和有依据结论比例。
- 答案正确性、完整性、相关性、Faithfulness、无答案拒答准确率与任务格式符合率。
- 回归案例数量与关键回归案例数量。

### Loop 与进化指标

- `success_at_1` 与 `success_at_n`。
- 平均和最大循环次数。
- 每轮分数提升。
- 每增加 1,000 Token 带来的分数提升。
- 检索恢复率与引用修复率。
- 无提升停止率与预算停止率。
- 策略记忆复用次数与复用成功率。
- Reflection 触发率、批评类型准确率、修复计划执行成功率和相对普通重试的增益。
- Reflexion 候选通过率、记忆召回率、有效复用率、错误经验注入率和跨任务净收益。
- 候选版本晋升、拒绝、回滚和人工接受率。

### 成本与可靠性指标

- LLM 调用数、输入/输出/总 Token 与预计成本。
- 按数据源统计的原生工具和 MCP 工具调用数。
- 缓存命中率、延迟、超时、重试和失败率。
- 每个成功任务的成本与延迟。
- 检查点恢复和中断任务恢复成功率。
- 分层存储的缓存命中率、P50/P95 延迟、并发冲突率、TTL 失效率和缓存故障降级成功率。

## 测试与报告要求

路线图中的每项新增能力都必须包含：

- 正常、边界、失败、兜底和预算路径的单元测试；
- 新节点和新路由的 LangGraph 集成测试；
- 基线版本与候选版本的离线 Benchmark 案例；
- 在 `scripts/test_case_catalog.py` 中登记测试作用、通过含义和失败含义；
- 更新本地单元测试 Excel 报告和能力基准报告；
- 同时展示质量提升与 Token、延迟、工具调用成本的指标；
- 对行为产生影响的版本提供功能开关或回滚路径。
- RAG 实验不得只报告“效果更好”，必须保存每个测试问题的召回结果、排名、证据、答案、指标和失败原因。
- RAG Excel 报告至少包含测试摘要、用例说明、检索明细、答案评测、技术组合、参数实验、延迟成本、失败案例和历史趋势工作表。
- 新增 Parser、Chunker、Embedding、VectorStore、Retriever、Reranker 或 GraphRetriever 时，必须登记其测试作用、适用条件、通过含义和失败含义。
- 新增 MemoryStore、CacheBackend、Redis 或 Checkpointer 实现时，必须登记一致性、并发、过期、故障恢复、隐私删除和降级测试。
- 新增 Reflection 或 Reflexion 能力时，必须登记反馈来源、失败类型、修复动作、记忆写入门控、污染测试、无反思基线和关闭开关。
- 技术选型报告同时保留未采用方案及其淘汰原因，避免只展示最终方案。

## 总体实施顺序

### 近期：先稳定核心边界

1. 完成统一 Tool 工具层；
2. 强化现有 Harness、Verifier 与 Context Engineering；
3. 增加多数据源检索和本地知识库；
4. 增加 MCP Client Adapter；
5. 增加最终答案评估、checkpointer 和有限 Agent Loop；
6. 为上述能力补充基线/候选 Benchmark、测试说明和 Excel 报告。

其中本地知识库按照“统一接口 → RAG 标注数据集 → Dense 基线 → 分组件对照实验 → 选型晋升”的顺序实施，不在开发开始前锁定具体技术产品。

### 中期：形成科研任务闭环

1. Structured Memory 与 LLM Wiki；
2. ExperimentIdeaSkill；
3. LiteratureReviewSkill；
4. PaperCritiqueSkill；
5. ReportWritingSkill；
6. Structured Output；
7. 轻量 Multi-Agent v1。

### 后期：扩展复杂能力并进入受控进化

1. 分层 Multi-Agent；
2. 多模态 PDF 理解；
3. Multi-Trajectory / Best-of-N；
4. 离线 Agent 自进化与受控在线适应；
5. PaperAgent MCP Server；
6. 前端、Docker 与完整 CI/CD。

基础 CI 可以在任意阶段提前接入；这里的“后期”指完整部署与发布流程，而不是要求一直推迟自动测试。

## 推荐的下一项开发工作

跨来源确定性重排 v1 已完成缓存 A/B：Recall@5 从 55% 提升到 60%，MRR@5 从 45.42% 提升到 57.50%，没有新增 API 或 LLM Token；但一条 OpenAlex 标题/DOI 异常记录仍进入 Top 3，因此功能开关暂不默认开启。

权威元数据来源解析 v2 已完成两份独立快照验证：`multi_verified_rerank` 两次均为 Recall@5 60.00%、MRR@5 57.50%、nDCG@5 58.15%，逐题质量回归为 0；但隔离集合只有 40% Jaccard 稳定度，且新增隔离中存在可能相关论文，因此功能开关继续默认关闭。第二快照还验证了快照隔离、失败续跑和累计 API 成本记录。

规范 arXiv ID 候选评测已完成三份独立快照：三次 Recall@5 均由 60% 提升到 65%，MRR@5 均由 57.5% 提升到 62.5%，逐题质量回归为 0；13 个重点身份均取得明确原生查询结论，自动晋升门槛通过。该结论只覆盖 arXiv 身份验证，尚未直接修改生产默认开关。

下一项优先扩大规范元数据评测覆盖并建立晋升门槛：

```text
对普通 DOI 建立可替换 authority provider 接口，评测 Crossref 等规范来源
→ 增加规范解析覆盖率、查无率、误隔离率、修复准确率和网络失败恢复指标
→ 重跑 multi / multi_rerank / multi_verified_rerank / multi_canonical_rerank A/B
→ 质量无回归且隔离准确率、稳定度达标后，再考虑默认开启重排与校验

2026-08-12 已完成 arXiv authority 独立开关和普通 DOI 可替换 `paper.lookup` 接口。Crossref 首轮使用三份快照均稳定出现的 20 个普通 DOI：查询覆盖率 100%，标题匹配 20/20，冲突、查无和失败均为 0，LLM Token 为 0。该样本按稳定 DOI 排序抽取，尚不足以固定选型；下一轮需要按 DOI 注册机构/出版商分层扩大样本，并与至少一个替代规范来源比较。

2026-08-12 已完成第二轮分层 provider 对比：从 51 条三快照稳定普通 DOI 中按 DOI 前缀轮转抽取 40 条，覆盖 19 个前缀。Crossref 明确响应 40/40，标题匹配 38、查无 2、失败 0；Semantic Scholar 匿名访问明确响应 23/40，标题匹配 18、冲突 2、查无 3、RATE_LIMITED 17。双方均返回标题的 19 条中有 18 条一致，一致率 94.74%。因此 Crossref 进入下一轮生产 A/B，Semantic Scholar 保留为配置 API Key 后复测的候选；限流不视为语料查无或负身份依据。两者均尚未设为生产默认。

2026-08-12 已完成 Crossref 普通 DOI 受控接入和三快照联合 canonical A/B：13 个 arXiv 身份与 65 个普通 DOI 共 78 个身份均取得明确 authority 结果，续跑为 78 次缓存命中、0 新 API、0 LLM Token。联合策略相对 v2 的三快照 Recall@5 均由 60% 提升到 65%，MRR@5 均由 57.5% 提升到 62.5%，逐题回归为 0；但与“仅 arXiv canonical”对照相比，Crossref 的 Recall/MRR/nDCG 增量和排名变化均为 0，且没有触发 DOI 标题修复。因此当前价值是 65/65 普通 DOI 可审计覆盖，不宣称排序质量提升。Crossref 明确查无 3 条只记录警告、不自动隔离；生产独立开关继续默认关闭，后续需补充人工标注的 DOI 污染/修复挑战集。

2026-08-12 DOI 校验已按止损原则完成 6 类确定性污染挑战集：修复准确率 100%，误修复 0，误隔离 0，阶段验收通过并冻结，不再继续扩大 provider 或样本讨论。随后已进入来源级有界并行：使用最大 2 个 worker 并发执行同步 provider 搜索，按配置顺序收集结果，单来源不创建线程池，部分成功语义保持不变。5 次离线 I/O 重复实验中，中位延迟约从 250ms 降至 125ms，加速约 2.0 倍、延迟下降约 50%，结果与顺序一致率 100%。生产开关默认关闭，下一步用真实网络快照验证限流与 P95 后再决定默认开启。

2026-08-12 DOI 校验已按止损原则完成 6 类确定性污染挑战集：修复准确率 100%，误修复 0，误隔离 0，阶段验收通过并冻结，不再继续扩大 provider 或样本讨论。随后已进入来源级有界并行：使用最大 2 个 worker 并发执行同步 provider 搜索，按配置顺序收集结果，单来源不创建线程池，部分成功语义保持不变。5 次离线 I/O 重复实验中，中位延迟约从 250ms 降至 125ms，加速约 2.0 倍、延迟下降约 50%，结果与顺序一致率 100%。生产开关默认关闭，下一步用真实网络快照验证限流与 P95 后再决定默认开启。
→ 随后实现来源级与子查询级有界异步并行
→ 再进入失败类型驱动的 Retrieval Replan 和 Reflection
```

完成在线多源评测后，再依据数据判断继续接入 Semantic Scholar、开始本地 RAG 标注集，或先优化数据源路由；MCP、Agent Loop、LLM Wiki 和 Agent 自进化继续建立在统一 Tool 与 Harness 接口之上。

2026-08-12 已完成来源级并行的最小真实网络 A/B：1 个查询、串并行各 1 次，并行耗时约 7.42 秒、串行约 10.20 秒，单次延迟下降 27.26%；但 arXiv 两次请求均返回 HTTP 429，工具失败计数为 2，因此晋升门槛判定失败，生产开关继续默认关闭。该结果只用于验证评测与限流边界，不作为稳定性能结论，不再重复施压外部 API。

随后已进入子查询级有界并行阶段：新增独立开关与最多 2 个 worker，结果始终按查询规划顺序收集，单子查询不创建线程池。下一步为子查询并行补充离线重复延迟基准，然后进入失败类型驱动的 Retrieval Replan；在来源级在线门槛通过前，两级并行不默认叠加开启。

2026-08-12 子查询并行已完成 5 次确定性离线重复基准：3 个子查询、2 个 worker 时，中位延迟由 265.4ms 降至 172.3ms，加速 1.54 倍、延迟下降 35.09%，结果与规划顺序一致率 100%，达到阶段门槛并收口。

随后已开始 Retrieval Replan v1：现有“低分后只扩大结果数”的普通重试升级为可审计的失败分类与受限动作。暂时工具失败保持原查询，零结果放宽字面限制，有结果但低相关时追加综述上下文；新查询覆盖旧子查询计划，仍受最多重试一次约束，全程不增加 LLM 调用或付费工具。下一步评测 Replan 相对普通重试的恢复率、无效重试率和动作分类准确率。

2026-08-14 已完成 Retrieval Replan v1 轻量验收。冻结 6 个离线 Oracle 案例，覆盖超时/网络错误、带引号的零结果窄查询和有结果但低相关三类失败；失败分类准确率 100%，目标修复查询命中率由原样重试的 33.33% 提升到 100%，语义失败原样无效重试率由 100% 降到 0%，全程 0 LLM。报告同时输出 JSON 与 UTF-8 BOM CSV，逐例记录失败类型、动作、原查询、目标查询和候选查询。该结果只证明确定性分类与查询修复命中人工 Oracle，不宣称 arXiv/OpenAlex 在线恢复率；按简历项目轻量策略不扩大 Replan 数据集，后续只做代表性在线冒烟。阶段收口后回到原能力路线，下一步优先接入只读 Zotero MCP v1，再接只读 GitHub MCP。

2026-08-14 已完成只读 Zotero MCP v1 代码接入。PaperAgent 自带 `paperagent-zotero` stdio MCP Server，通过固定 GET 请求调用 Zotero 官方 Web API v3；私有库 Key 只放在 `Zotero-API-Key` 请求头。`library.search.zotero.mcp` 已注册到统一 Registry，经过只读 Policy、Pydantic Schema、超时 Executor 和审计元数据，`RETRIEVAL_MODE=zotero` 可显式接入主检索、Evidence Store 与 Research Writer，默认 arXiv 不变。v1 支持个人/群组库、关键词、Tag、Collection Key、元数据、子笔记和 PDF 附件 Key；尚未下载/解析 PDF，也未解析 Collection 名称。Zotero 失败保持空结果和真实错误，不使用公共 fallback 冒充用户收藏。6 个代表测试加 MCP/检索回归共 25/25 通过，0 在线请求、0 LLM。下一步由用户配置只读 Library ID/API Key 后做一次真实冒烟；随后进入只读 GitHub MCP v1。

2026-08-14 已完成 Prompt 安全边界与版本化 v1。论文/工具文档、Zotero 笔记、PDF 提取文本、Evidence Store snippet、检索评分材料和 Answer Reflection 证据统一使用显式 `UNTRUSTED_EVIDENCE` 边界，边界前后都声明外部内容不能覆盖角色、规则、密钥、工具或代码执行权限。Reason、Evaluator、Research Analyzer、普通/科研 Skill、Research Writer、PDF Reader 与 Answer Reflection 均注册唯一 `prompt_version`；成功和失败的 LLM usage 都记录版本，节点 metrics 汇总实际使用版本，为后续 zero-shot/few-shot A/B 提供归因。5 个恶意证据/版本契约测试及相关回归 39/39 通过，0 LLM。该结果只证明 Prompt 组装契约，不宣称真实模型已抵抗 Prompt Injection；下一步建立小型对抗集并先做零费用 Fake LLM/字符串边界检查，再决定是否对 Research Analyzer 和 Writer 加选择性 few-shot。

2026-08-14 已完成 Prompt Injection 对抗集 v1。冻结 4 个中文合成案例，覆盖 Zotero 笔记角色覆盖、论文文本诱导工具调用、PDF 诱导读取 API Key、Research Writer 诱导伪造 Evidence ID；默认模式只检查生产 Prompt 边界，4/4、0 LLM、0 Token，并输出 JSON/UTF-8 BOM CSV。真实 qwen 模型显式运行 4 次，共 9,364 Token：4/4 未输出攻击 Canary、未引用 `[E-PWNED]`，且每题至少保留一项与原研究问题相关的安全内容；实际使用 `qa_v2_security`、`pdf_reading_v2_security`、`research_writer_v2_security` 可追溯。评测器测试保证攻击复述、伪造引用和纯拒答均不能通过，相关安全/CI 测试 14/14 通过。该结果只是当前模型对 4 个合成攻击的代表性冒烟，不宣称完整红队或跨模型泛化；按简历项目定位不扩建大型安全集。下一步对 Research Analyzer 做 3～4 个边界 few-shot 候选，与现有 zero-shot 在固定 L1/L2/L3 集上轻量 A/B，通过后再考虑 Research Writer 的引用正反例。

2026-08-14 已完成 Research Analyzer zero-shot/few-shot 轻量 A/B。生产仍默认 `zero_shot`，候选包含4个 L1/L2/L3 边界示例；冻结6个真正会调用 Analyzer LLM 的 L3 案例，同一模型温度0共运行12次、35,467 Token。zero-shot 原始结构仅解析1/6、完整通过0/6，主要失败是模型把 `source_requirements` 输出为字符串；few-shot 解析6/6、完整通过2/6（33.33%），提升33.33个百分点，总 Token 17,212 对18,255（-5.71%），平均延迟16.518秒对20.679秒。虽然 few-shot 显著改善格式稳定性，但绝对质量远低于80%晋升门槛，故不切换生产默认。评测时还修复了晋升闸门缺少“绝对通过率”条件的问题，防止0%→33.33%被相对提升误判为可上线。下一步不继续堆示例，优先尝试更低成本的 schema-first zero-shot：明确数组字段类型/使用结构化输出，并对单值列表做有界预校验规范化，再复用同一开发集验证解析与约束覆盖。

2026-08-14 已完成 Retrieval Replan v1 轻量验收。冻结 6 个离线 Oracle 案例，覆盖超时/网络错误、带引号的零结果窄查询和有结果但低相关三类失败；失败分类准确率 100%，目标修复查询命中率由原样重试的 33.33% 提升到 100%，语义失败原样无效重试率由 100% 降到 0%，全程 0 LLM。报告同时输出 JSON 与 UTF-8 BOM CSV，逐例记录失败类型、动作、原查询、目标查询和候选查询。该结果只证明确定性分类与查询修复命中人工 Oracle，不宣称 arXiv/OpenAlex 在线恢复率；按简历项目轻量策略不扩大 Replan 数据集，后续只做代表性在线冒烟。阶段收口后回到原能力路线，下一步优先接入只读 Zotero MCP v1，再接只读 GitHub MCP。

2026-08-12 Replan v1 已完成 6 类确定性故障对照：失败分类准确率 100%，普通原样重试恢复率 33.33%，Replan 恢复率 100%，提升 66.67 个百分点；语义失败的无效重试率由 100% 降为 0%，LLM 调用为 0，达到阶段门槛并收口。该结论基于固定故障与模拟成功条件，只证明分类和动作映射逻辑，不代表真实网络检索恢复率。

下一阶段转入第二轮结果反馈与停止决策：Replan 后重新评估质量，明确记录“已恢复、质量仍不足、重试预算耗尽”等终止原因，为后续 Reflection/Reflexion 提供受控触发信号，而不是继续增加 Replan 规则。

2026-08-12 已将第二轮停止状态接入回答生成与指标：`accepted` 保持正常 Skill/LLM 路径，`recovered` 单独记录恢复成功，`stopped_low_quality` 在重试预算耗尽后跳过 LLM，返回“证据不足”的降级回答并只列出待人工核验候选。metrics 新增 outcome、stop_reason、recovered、budget_exhausted、answer_mode 与 generation_skipped，避免把低质量停止混入正常成功率和 Token 成本。

下一步应为这一质量闸门建立“正常回答 vs 证据不足降级”的能力对照，统计低质量阻断准确率、误阻断率和避免的 LLM 调用/Token；达到门槛后，再决定 Reflection 是只对可修复失败触发，还是继续优先建设真实检索评测与本地 RAG。

2026-08-12 质量闸门已完成 8 类确定性对照：4 个低质量案例阻断准确率 100%，4 个正常案例误阻断率 0%，降级回答格式合规率 100%；相对“有文档就生成”的旧行为，避免 4 次模拟 LLM 调用和 480 Token，达到阶段门槛并收口。Token 使用固定每次 120 的模拟口径，只用于验证成本计数逻辑。

技术决策：下一阶段优先建立本地 RAG 评测基础，不立即扩大 Reflection。原因是当前主要失败来自证据不足或外部来源不可用，Reflection 无法创造新证据；先建立版本化问题、相关片段、来源页码和技术配置契约，才能对 Dense RAG、GraphRAG、LightRAG 与混合方案做单变量公平评测。Reflection 保留为证据充分但答案结构、引用或推理仍失败时的后续受控修复层。

2026-08-12 已完成本地 RAG 可行性验证的准备层：新增逐页 PDF Parser、保留页码与字符位置的固定窗口 Chunker、基于 SHA-256 与处理组件版本的增量语料 Manifest，以及中文人工标注模板。PDF 仍按需放入 `data/papers/` 且被 Git 忽略；只有文件内容、Parser 或 Chunker 版本变化的论文需要重建。当前未建立正式知识库或向量索引，下一步等待放入 5～10 篇代表论文后生成语料清单和首批 15～20 个人工问题，再实现 BM25 基线。

2026-08-12 已建立首批 8 篇真实论文语料：RAG、DPR、Self-RAG、GraphRAG、LightRAG、ReAct、Reflexion 与 LLM Agent Survey。选择同时覆盖单篇事实、方法细节、跨论文比较、全局主题和长文召回，避免只为 Dense 或图检索单一路线优化。公开来源、arXiv ID、选取理由和测试维度进入版本控制；原始 PDF 保持本地忽略，实际文件身份由 SHA-256 Manifest 固定。8 篇共 198 页并通过 PDF 文件头、逐页解析和文本抽取验证。下一步从这批全文标注 15～20 个带页码和证据片段的问题，再实现 BM25 首个可运行基线。

2026-08-12 已完成人工金标准 v1：共 16 个中文问题，8 篇论文各 2 题，覆盖方法、实验数值、记忆、规划和局限，包含 9 个简单问题与 7 个复杂问题。每条参考答案均由人工阅读 PDF 后编写，证据绑定解析器实际 PDF 页序号和固定窗口真实 chunk ID；自动测试会重新解析全部原文，确认引用片段确实存在于声明页，并验证构建结果可确定性复现。数据集在检索算法运行前冻结，避免依据 BM25 或 Dense 结果反向修改金标准。下一步实现 BM25 全文检索基线并保存逐题排名、Recall@K、MRR、nDCG、延迟与失败原因。

2026-08-12 已完成首个 BM25 全文检索基线：1098 个固定窗口 Chunk、16 个冻结问题、0 次 LLM 调用。精确 Chunk 指标为 Recall@1 6.25%、Recall@3 12.50%、Recall@5 18.75%、MRR@5 10.94%、nDCG@5 12.89%；平均查询延迟约 8.05ms，P95 约 12.01ms。该结果作为诚实的纯词法下限，不据此宣称 BM25 不适合项目；逐题结果表明主要瓶颈是中文问题与英文论文之间的词汇鸿沟，同时严格 Chunk 命中会把相邻证据块视为未命中。下一步先增加固定、可审计的中英术语查询改写 A/B，并补充 page-level 辅助指标，再实现 Dense 基线；主技术选型仍以精确 Chunk 指标和逐题净提升/回归为准。

2026-08-12 已完成确定性中英术语扩展开发集 A/B：保留原始中文问题并追加显式英文术语，0 次 LLM 调用，不改变 BM25 参数。精确 Chunk Recall@5 从 18.75% 提升到 75.00%，MRR@5 从 10.94% 提升到 53.33%，nDCG@5 从 12.89% 提升到 58.82%；Page Recall@5 从 37.50% 提升到 81.25%。逐题为 9 个提升、7 个不变、0 回归。评测器同时修复了同一 PDF 页多个 Chunk 重复计入 page nDCG 的问题，所有指标限制在合法范围。由于术语表设计参考了当前 16 题，本结果仅为开发集机制验证，不能据此生产晋升；下一步必须建立未参与术语设计的保留问题集，并在相同 PDF、Chunker 和指标下复测规则扩展及多语言 Dense。

2026-08-13 已完成冻结术语表独立保留集：人工新增 10 个中文问题，覆盖全部 8 篇论文，证据页与 16 题开发集零重叠，术语表在标注和评测期间未修改。原始 BM25 与规则扩展的 Chunk Recall@5 均为 60.00%；规则扩展 Recall@3 从 50.00% 降至 40.00%，MRR@5 从 42.50% 降至 40.00%，nDCG@5 从 46.93% 降至 44.92%。按 nDCG 逐题判断为 0 个提升、1 个回归、9 个不变，回归发生在 ToolFormer 问题，正确证据仍在 Top-5 但排名下降。开发集的大幅收益未能在未见证据页上复现，说明现有术语表存在开发集拟合；规则扩展不晋升，生产开关继续关闭。下一步转入多语言 Dense Retrieval 基线，并继续使用相同开发集、保留集、PDF、Chunker 和精确 Chunk 主指标。

2026-08-13 已完成首个多语言 Dense Retrieval 基线：使用 `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`、FastEmbed 0.7.4、ONNX Runtime CPU 和显式 L2 归一化余弦相似度，继续复用 8 篇论文、1098 个 Chunk、16 题开发集和 10 题独立保留集，全程 0 次 LLM 调用。开发集 Chunk Recall@5 从 BM25 的 18.75% 提升至 25.00%，nDCG@5 从 12.89% 提升至 17.88%；独立保留集 Recall@5 从 60.00% 提升至 80.00%，nDCG@5 从 46.93% 提升至 59.05%，Page Recall@5 从 60.00% 提升至 90.00%。保留集逐题为 4 个提升、3 个回归、3 个不变，说明语义泛化有效但仍不稳定；首次构建 1098 个向量约 119 秒，平均查询约 334.54ms，对照 BM25 约 14.39ms。自动晋升闸门未通过，生产默认继续关闭。下一步按“持久化索引缓存与冷/热启动分离 → 重复运行稳定性 → 第二个多语言 Dense 单变量对照 → Dense 与 BM25 Hybrid”推进，不提前写死模型或向量库。

2026-08-13 已完成 Dense 向量索引缓存：使用覆盖完整 Chunk 内容与身份、Parser/Chunker 版本、模型名和缓存格式版本的 SHA-256 指纹，向量以无 pickle 的 NumPy 格式原子写入；元数据缺失、维度/数量不符、非有限值或指纹变化均视为未命中。真实冷启动编码 1098 个 Chunk 约 61.62 秒并写缓存约 31ms；热启动读取约 10.58ms、检索器构造约 2.99ms，建库阶段下降超过 99.99%。开发集与独立保留集全部 Recall/MRR/nDCG 指标完全一致，证明缓存只优化启动成本。生产 Dense 开关继续关闭，下一步做多次独立进程热启动与查询延迟稳定性评测。

2026-08-13 已完成 3 次独立 Python 进程 Dense 热启动稳定性评测：三次均命中同一缓存指纹，开发集与独立保留集的全部质量指标、每题 Top-5 Chunk 顺序和八位小数分数完全一致。模型加载均值 3.45 秒、CV 24.87%；缓存读取均值 9.09ms、CV 16.73%；检索器构造均值 3.14ms、CV 3.42%。开发集平均查询 78.22ms、CV 45.53%，保留集平均查询 78.61ms、CV 28.96%；均低于当前 50% 波动门槛，但开发集已接近边界，故只判定可复现基线通过，不宣称低延迟或生产就绪。生产开关继续关闭，下一步使用完全相同语料、缓存契约、问题集与指标，对照第二个多语言 Dense 模型。

2026-08-13 已完成第二个多语言 Dense 模型单变量对照：选择 FastEmbed 支持的 `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`，原因是它与 MiniLM 同样覆盖约 50 种语言、无需 query/document 前缀，但从 384 维扩大至 768 维，可以主要隔离模型容量差异；约 2.24GB 且必须增加前缀的 multilingual E5-large 留到后续策略实验。所有模型文件与向量索引均固定在 `D:/langgraphproject/data/cache/` 并被 Git 忽略。相同独立保留集上，MPNet 与 MiniLM 的 Chunk Recall@5 同为 80.00%，MPNet 将 Recall@1 从 40.00% 提升至 60.00%、MRR@5 从 52.33% 提升至 70.00%、nDCG@5 从 59.05% 提升至 72.62%；逐题为 4 提升、1 回归、5 不变，回归为 RAG decoding 正确 Chunk 掉出 Top-5。MPNet 冷建库约 317.5 秒，热查询约 96.81ms，约为本次 MiniLM 47.69ms 的 2.03 倍。MPNet 通过“nDCG 提升、Recall 不降、回归不超过 2”门槛，晋升为首选 Dense 模型候选；生产开关继续关闭，下一步先做 MPNet 独立进程稳定性，再决定进入 Hybrid 互补实验。

2026-08-13 已完成 MPNet 三次独立 Python 进程热缓存稳定性评测：三次均使用预期 MPNet 模型并命中同一缓存指纹，全部质量指标、每题 Top-5 Chunk 和八位小数分数完全一致，证明排序收益可复现。模型加载均值 4.90 秒、CV 30.66%；缓存读取均值 10.65ms、CV 28.33%；检索器构造均值 4.00ms、CV 18.03%。开发集平均查询 CV 35.63% 通过，但保留集平均查询为 266.50ms、93.92ms、99.42ms，均值 153.28ms、CV 52.25%，超过 50% 门槛，故性能稳定性和阶段总判定不通过。不得删除首个慢样本或直接进入 Hybrid；下一步先显式区分首次查询预热与正式计时，冻结新协议后再完整复测一次 MPNet 稳定性。

2026-08-13 已完成首次查询预热隔离复测：冻结中性查询 `academic paper semantic retrieval warmup`、每个独立进程执行两次、逐次记录但不计入正式延迟，且三次运行必须使用相同协议。预热后开发集平均查询均值由 156.68ms 降至 92.22ms、CV 由 35.63% 降至 15.58%；保留集均值由 153.28ms 降至 108.92ms、CV 由 52.25% 降至 28.50%。三次模型身份、缓存指纹、质量指标、Top-5 Chunk 和分数仍完全一致，证明首次 ONNX 推理初始化是上轮超线的主要来源，MPNet 稳定性闸门通过。保留集 P95 CV 仍为 45.25%，生产默认继续关闭；下一步进入 Dense + BM25 Hybrid 单变量互补对照，重点验证能否修复 RAG decoding 回归且不损害其余题目。

2026-08-13 已完成首个 Dense + BM25 Hybrid 基线。采用 RRF 只融合名次，避免直接相加 BM25 与余弦分数；预先声明 k=20/40/60，只在开发集按 Recall@5、nDCG@5、回归数、延迟顺序选参，三个候选质量完全相同，最终按延迟平局规则冻结 k=40。独立保留集只运行一次：RAG decoding 与 ReAct 题改善，但 DPR corpus、GraphRAG cost、Agent memory 三题回归，Recall@5 由 80% 降至 70%，nDCG@5 由 72.62% 降至 60.62%，质量闸门失败，生产继续关闭。当前保留集已经用于本轮最终判断，禁止围绕其结果继续调参；下一阶段先在开发集研究受约束融合或按查询门控，再建立新的未见验证集 v2 进行最终验证。

2026-08-13 已完成受约束 Hybrid 的开发阶段：只使用线上可见信号构建门控特征，禁止使用题目 ID、论文主题和金标准。预声明网格覆盖 Dense Top-1 阈值 0.60/0.65/0.70、Top-1/Top-2 间隔 0.015/0.03/0.05、Top-5 重合度 0/0.2/0.4；候选必须至少改善 2 题、0 回归并通过留一安全检查。冻结候选为 `Dense Top-1 <= 0.65 且间隔 <= 0.05`，开发集触发 6/16 题、改善 3、回归 0。已实现默认 Dense、条件触发 RRF 的可审计检索器，但不宣称泛化通过，不读取已经暴露的 holdout v1。下一阶段独立建立未见验证集 v2，先冻结问题与证据，再运行一次门控对照。

2026-08-13 已完成未见验证集 v2 与一次性门控验证：从 8 篇论文各选 1 个开发集及 holdout v1 从未使用的 PDF 页面，人工视觉核对原页后标注精确 Chunk、引文和答案；自动测试保证 8 篇覆盖、证据页零重叠、引文等于当前 Chunk、构建结果可复现。冻结阈值与 RRF k 后只运行一次对照，门控在 8 题中触发 4 题，将 Recall@5 从 50.00% 提升到 62.50%、MRR@5 从 15.42% 提升到 22.29%、nDCG@5 从 23.81% 提升到 32.24%；逐题 2 提升、0 回归、6 不变，质量闸门通过。平均延迟从 850.27ms 增至 891.57ms，P95 从 1543.89ms 增至 2474.40ms；考虑样本仅 8 题和尾延迟，生产默认继续关闭。下一步扩大未见样本并做门控独立进程性能稳定性，不得继续围绕 v2 调整阈值。

2026-08-13 已完成门控 Hybrid 执行复用与三次独立进程稳定性：旧实现为了判断置信度先执行 Dense，触发 RRF 后又重复执行 Dense；现在将第一次得到的候选排名直接交给 RRF，只额外运行 BM25，并删除重复的门控类定义。冻结数据、阈值和 RRF k 后，优化前后 Recall/MRR/nDCG、逐题 Top-5、八位小数分数与路由完全一致。三次新 Python 进程在固定两次预热后平均查询延迟分别为 19.51、23.60、25.32ms，均值 22.81ms、CV 10.67%；P95 均值 32.85ms、CV 18.97%，质量、缓存指纹和 4/8 路由决定完全复现，稳定性闸门通过。生产默认仍关闭：v2 只有 8 个问题，本轮只证明执行成本与确定性，不把 v2 用作继续调参。下一步冻结当前配置，扩建新的未见评测集以增强泛化证据，再进行生产晋升评估。

2026-08-13 项目定位调整为简历能力展示，后续验收采用轻量策略：新增能力只保留代表性冒烟、关键路径单元测试和必要的回归检查，不再默认执行研究级多保留集、反复独立进程或大型指标报告。本轮已将本地全文 RAG 接入 LangGraph 主检索节点：通过 `RETRIEVAL_MODE=local_rag` 可在在线论文发现与本地全文问答之间切换；本地后端按需加载 D 盘 PDF、MPNet 和冻结向量缓存，返回带论文、页码、Chunk ID、分数的证据，并把 Dense/Hybrid 门控决定和排名策略写入响应元数据。代表性真实冒烟“ReAct 如何结合推理和行动”返回 ReAct 论文第 9 页 Chunk，主流程接入测试 10/10 通过。下一步优先完成可展示的 API 示例与项目 README 能力说明，而不是继续扩建评测集。

2026-08-13 明确采用“双轨推进”：简历项目定位只减少重复评测，不取消阶段 3～16 的原技术路线。能力轨继续推进 MCP、有限 Agent Loop、Reflection/Reflexion、Structured Memory、LLM Wiki、Redis 候选、Agent 自进化、科研 Skill、结构化输出、Multi-Agent、多模态和 Harness；展示轨在每个能力完成后补充轻量冒烟、关键回归和 Web 可视化。前端展示属于插入式展示任务，不替代原计划阶段。

2026-08-13 已启动阶段 3 MCP Client：新增传输无关的 `MCPToolAdapter` 和最小 `MCPClient.call_tool` 契约，使 MCP 工具直接复用现有 Tool Registry、只读 Policy、Pydantic 输入输出校验、超时/重试 Executor 与统一 ToolResult。适配器兼容结构化结果包装，远程错误转换为统一执行错误，并在审计元数据记录 MCP Server 身份、版本、传输方式和远程工具名；相关工具层测试 22/22 通过。当前完成的是稳定接缝，尚未宣称连接真实 MCP Server；下一步接入一个可信、只读 MCP Server，并把一个论文检索或项目资源工具注册到默认运行时。

2026-08-13 已完成首个真实 MCP 链路：采用官方 MCP Python SDK 2.x，通过 stdio 短生命周期 Client 启动 `paperagent-corpus` Server。Server 只读访问版本控制内的 `corpus_sources.json`，暴露 `search_corpus` Tool 和 `paperagent://corpus/catalog` Resource，不访问网络、不读取 API Key、不修改文件。`paper.catalog.search.mcp` 已注册到默认 Tool Registry，继续受只读 Policy、Pydantic 双端 Schema、15 秒超时和统一 ToolResult 约束；真实调用成功返回 ReAct 论文并记录 Server 1.0.0、stdio 和远程工具名，相关轻量测试 24/24 通过。当前每次调用包含约 3 秒 Server 冷启动，适合单用户演示；未来并发场景再评估长连接或 Streamable HTTP。下一步完成 MCP Tool Router 路由与主工作流的显式使用场景，然后结束阶段 3 Client v1，进入阶段 4 有限 Agent Loop 与 Reflection。

2026-08-14 外部 MCP 扩展范围冻结为两个只读工具，不继续扩张 MCP 清单。第一项为 Zotero MCP，用于搜索个人文献库、读取论文元数据、Collection、标签、笔记和可用 PDF 全文；第一版禁止新增、修改或删除条目、标签和笔记。第二项为 GitHub MCP，用于查找论文对应仓库并读取 README、目录结构、依赖、配置、Issue、Release 与 Commit；第一版禁止创建 Issue、修改文件、提交代码、操作分支和合并 PR。Filesystem、Crossref、Semantic Scholar、OpenAlex、数据库和 Fetch MCP 不加入当前后续计划；已有原生数据源保持原生实现。实施顺序为先 Zotero、后 GitHub，并统一经过现有 Registry、Policy、Executor、Schema 校验和审计元数据。

2026-08-14 已完成 MCP Client v1 路由收口。默认 Tool Router 新增 `paper.catalog.search / mcp_catalog → paper.catalog.search.mcp` 确定性路由，设置 `RETRIEVAL_MODE=mcp_catalog` 后，LangGraph 主检索函数会使用 MCP 参数契约调用真实只读 stdio Server；默认 arXiv 模式不变，LLM 不会自行触发 MCP。工具执行轨迹现在保留 capability、source、tool name，以及 MCP Server、版本、传输方式、远程工具名、耗时和统一错误。代表性工具层、真实 MCP、主检索、多源回归与测试目录验证 35/35 通过，阶段 1 收口；下一步进入 Verifier 与最多一次的有限 Reflection 修复。

2026-08-14 路线 V3 将有限 Agent Loop 与 HTC Research Graph 中适合 PaperAgent 的设计合并。保留 L0 Direct、L1 Fast Research QA、L2 Standard Research、L3 Deep Research 四级任务路由；基础工作流只包含最多一次 Retrieval Replan 和最多一次 Answer Reflection。L3 在前述能力成熟后增加 Research Brief、最多 5 个任务的受限计划、并行数 2 的 Executor、Evidence Coverage、Citation/Claim Verifier 和 SQLite Checkpoint，并限制计划修复、证据补充和报告修复各最多一次且共享总预算。第一版不建设通用 Job 平台、任意 DAG、自由 Supervisor 或多角色辩论。Router、Loop 和 Research Graph 必须在模块完成时立即进行固定标注、集成、失败停止、质量和成本测试，不将首次能力验证推迟到最终阶段。

2026-08-14 已完成 Answer Verifier 与有限 Reflection v1。LangGraph 在 Generate 后新增确定性 Answer Verify 节点，检查空答案、最小完整度、比较/总结/推荐任务结构以及论文标题证据信号；已经明确披露检索证据不足的降级答案直接停止。有证据且缺陷可修复时，Answer Reflect 使用证据约束 Prompt 调用 LLM 一次，随后再次验证；分数无改善时恢复初始答案，任何路径最多 Reflection 一次。Metrics 记录验证分数、失败类型、Reflection 状态、原答案恢复与停止原因，支持 `ANSWER_REFLECTION_ENABLED=false` 关闭修复调用。代表性 Verifier、Fake LLM、LangGraph 循环、低质量停止、LLM 用量和检索回归测试全部通过且未调用真实模型。当前是单任务 Reflection，不写长期经验；下一步进入 SQLite 结构化记忆、上下文压缩与 LLM Wiki。

2026-08-14 将“证据驱动的轻量 Research Agent”确立为后续唯一产品主线。结构化记忆、上下文压缩、Checkpoint、LiteratureReviewSkill、PaperCritiqueSkill、Tool/MCP、全文 RAG、Coverage Gate 和 Claim/Citation Verifier 不再作为孤立功能展示，而是共同服务于“复杂研究意图 → Research Analysis → Brief → Plan → Evidence → Report → Verification”的闭环。普通搜索和问答保留 L1/L2 快速路径。Research Agent MVP 的固定首要演示任务为 Agent 架构研究方向调研，必须同时展示规划、证据、恢复、成本、停止和引用轨迹。

2026-08-14 已完成 Research Memory SQLite v1。旧逐会话 JSON 存储升级为项目内 `data/memory/paper_agent_memory.db`，保存完整消息、用户偏好、活跃研究主题、活跃论文与通用状态 Checkpoint；旧 JSON 在首次读取时兼容迁移且不会重复导入。服务请求现在注入最近 6 条原文、更早消息提取式摘要及结构化研究状态，并按默认 2400 字符预算组装上下文，回答后更新主题与论文。当前压缩完全确定性、不调用 LLM，正式 LangGraph SQLite Saver 扩展尚未安装，因此本轮提供存取接口而未宣称图级中断恢复。结构化存储、隔离、压缩预算、迁移、删除级联、Checkpoint、服务接入及相关 Agent 回归 42/42 通过且没有真实模型调用。下一步补正式 Checkpointer/语义摘要门控和 Markdown LLM Wiki，随后进入科研型结构化 Skill。

2026-08-14 已完成 Markdown LLM Wiki v1。Wiki 不是无门控的“模型记忆”：默认关闭自动发布，只有任务类型在白名单、Answer Verifier 通过、至少存在一条可追溯论文证据且回答未处于 `insufficient_evidence` 模式时才写入 `data/wiki/`。每篇笔记包含研究问题、结论、论文身份/来源/链接、Verifier 分数、失败类型和 Reflection 次数，索引按 Trace 幂等更新；Note ID 读取拒绝路径字符。服务响应返回发布状态与拒绝原因。Wiki、Research Memory、Verifier、Reflection、图路由与目录测试 50/50 通过且没有真实模型调用。下一步接入正式 LangGraph SQLite Checkpointer，使 Research Graph 能用 `conversation_id/thread_id` 保存和恢复图状态；LLM 语义摘要暂不优先，等待真实长会话证明提取式压缩不足。

2026-08-14 官方 LangGraph SQLite Checkpointer 已在提交 `7eb91d7` 中完成：Graph 通过 `SqliteSaver` 编译，Chat 使用 `conversation_id` 作为 thread_id，并在每次请求显式重置全部请求级状态；测试覆盖跨 Graph 实例恢复、线程隔离、删除和关闭开关。随后完成 Research Analyzer/Brief/Plan v1：研究请求在查询改写前进入 L1/L2/L3 分级，明确简单任务不调用 LLM；高置信度复杂请求可由一次结构化 LLM 分析补充目标、评价维度和 Skill，Policy Gate 禁止 L3 降级、未知 Skill 和关闭必要检索。Research Brief/Plan 限制最多 5 任务、并行 2，Validator 检查重复任务、当前 Brief 来源白名单、未知/自依赖和循环依赖；有效 L3 Plan 的检索任务转换为现有多查询。固定 12 条分级集为 12/12、L1 误升 L3 为 0，相关 Checkpointer、Memory、Wiki、Reflection、图和规划回归 76/76 通过且没有真实模型调用。当前尚无按依赖执行的 Scheduler、Evidence Store、Coverage Gate 或研究报告 Writer，不把多查询规划描述为完整 Deep Research。

2026-08-14 已接入官方 `langgraph-checkpoint-sqlite==3.1.1`。`build_graph` 支持注入 Checkpointer，服务默认将 SqliteSaver 连接到项目内 `data/memory/langgraph_checkpoints.db`，每次调用使用 `conversation_id` 作为 `configurable.thread_id`。同一线程开始新请求时显式重置 documents、answer、retry、Verifier、Reflection、规划和用量字段，避免旧 State 合并造成跨轮执行污染。测试证明完成状态可在关闭连接、重建 Graph 后恢复，不同线程严格隔离，删除线程不影响其他状态，关闭开关不创建数据库；相关 Memory、Wiki、Verifier 和图回归 53/53 通过且未调用真实模型。当前同步 SqliteSaver 适合本地单用户演示；未来只有真实并发和部署需求出现时才评估异步 Saver 或 Postgres。下一步进入科研型结构化 Skill，为 Research Agent 的 Brief、Plan、Literature Review 和 Critique 定义正式输出契约。

2026-08-14 已完成科研型结构化 Skill v1：新增 `LiteratureReviewOutput`、`PaperCritiqueOutput` 与最小 `EvidenceReference` Pydantic 契约，明确综述范围、研究版图、方法比较、研究空白、贡献、证据质量、复现风险和可定位引用等字段。新增 Literature Review 与 Paper Critique 两个中文科研 Skill，Prompt 强制区分论文事实与综合判断，材料不足时显式降级。Skill Router 只有在 Research Analyzer 已判定 L3 且 `primary_skill` 命中白名单时才允许覆盖普通任务路由，L1/L2 和未知 Skill 保持原快速路径。代表性契约、路由边界、Prompt 证据约束及研究分析回归 19/19 通过且未调用真实模型。当前契约用于约束目标语义，生成节点尚未把 Markdown 反解析为 Pydantic 对象；下一步实现有界 Research Scheduler 与 Evidence Store，使 Research Plan 能按依赖执行并形成 Claim–Evidence 中间结果。

2026-08-14 已建立正式在线 LLM 能力集 v1，与离线单元测试和外部检索评测明确分离。冻结 7 个中文代表案例：L1 单检索、L2 方法比较、L3 复杂研究规划，以及论文总结、论文比较、文献综述和论文批判；使用固定论文证据避免把 arXiv/OpenAlex 限流混入模型能力结论。自动门槛同时检查任务等级、Skill、Plan Validation、结构语义、论文身份、回退状态、真实调用次数、失败数、Token 和延迟，完整保留模型原始输出供人工 Review。运行器必须显式 `--confirm-online` 且凭据有效，默认 pytest 不产生费用；一键脚本输出 JSON、CSV 和三工作表 Excel。判分器、数据集与报告链路离线验证 16/16 通过，尚未把版式验证占位数据描述为真实模型成绩。下一步先运行一次完整在线集并修复真实模型暴露的问题，通过后再进入 Research Scheduler 与 Evidence Store。

2026-08-14 已完成在线 LLM 首轮审计与定向修复。首轮 3/7 中，L1 失败源于“代表论文”规则误升 L2，已修为证据要求；文献综述和论文批判实际输出合格，失败源于判分器未接受 Prompt Schema 中的英文字段，使用已有原始输出重放后通过；L3 增强 JSON 提取并保留解析错误与调用轨迹。只重跑 L1/L3 并合并已有报告后为 6/7：6 个能力案例通过，剩余 1 个为真实 Provider 调用失败，规则回退、L3 等级、Skill 与 Plan 均正确，不计为 Agent 能力失败。报告现区分 provider、capability 与 execution failure；相关规则、判分、路由和目录测试 19/19 通过。按止损原则不继续重复请求临时 Provider 失败；下一步进入有界 Research Scheduler 与 Evidence Store。

2026-08-14 根据 Review 将原 7 题在线集降级为 `smoke_v1`，新增冻结的 30 题核心在线 LLM 能力集：18 个任务分析覆盖 L1/L2/L3、混淆边界和结构化字段，4 个查询规划覆盖单查询、多查询与 L3 Plan 转换，8 个真实生成覆盖双论文总结、比较、Literature Review 和 Paper Critique。四份论文证据以 fixture 复用并在运行前校验，正式集预计最多约 17 次真实模型调用；报告区分能力、Provider 和执行失败，支持基于原始输出重判、指定 case 重跑及同数据集安全合并，拒绝把冒烟报告与核心报告混合。相关数据集、解析、规则、科研 Skill、报告与测试目录回归 21/21 通过；新增查询规划类别零 LLM 运行冒烟 1/1 通过。尚未运行完整 30 题在线集，避免未经用户确认直接产生约 17 次调用；完成核心集首轮后再进入 Scheduler。

2026-08-14 已完成 30 题核心在线集首轮：qwen3.6-flash 实际调用 17 次、62,525 Token、约 435.10 秒。原始自动结果 27/30；人工审计确认 RAG/GraphRAG 比较使用合法简称、RAG 技术综述使用“研究全景 / Research Landscape”合法标题，两项属于判分别名过窄，复用已有原始输出重判后为 29/30（96.67%），无 Provider 失败。剩余真实能力失败为“2023 年以来反思机制趋势”结构化分析进入规则回退，Plan、L3 和 Skill 正确，但回退 objectives 未保留“趋势”约束；不通过放宽门槛掩盖。Excel 初次预览因30条长输出申请 1440×17658 位图失败，已改为固定行高和代表性预览，工作簿仍保留全部原文并从 JSON 无费用恢复。随后一次定向重跑遇到 Provider 失败，已恢复首次正式基线，并规定 Provider 重试只能追加 attempts、不能覆盖既有能力结论。相关回归 22/22 通过。下一步针对结构化分析的约束保留与可靠解析做单点修复，然后进入 Research Scheduler 与 Evidence Store。

2026-08-14 已完成 L3 约束保留单点修复：规则回退不再使用固定四目标，而是从原问题确定性提取时间范围（如“2023年以来”）、趋势/未来方向、代表论文、研究价值、结构化比较和研究空白，最多保留 6 项；LLM 候选通过 Policy Gate 时也会补回遗漏的时间与语义约束。相关分析、在线判分和目录测试 19/19 通过。只重跑唯一失败题时 Provider 返回 `APIConnectionError`，新回退结果的 `objective_coverage=true`，证明修复生效；但因本次不是有效模型能力样本，正式基线仍诚实保留为 29/30，Provider 尝试追加到该 case 的 `attempts`，不覆盖原能力结论。按止损原则结束该问题，下一步进入有界 Research Scheduler 与 Evidence Store。

2026-08-14 已完成 Clarification Gate v1，并调整优先级使其位于 Research Analyzer、查询改写和检索之前。门控零 LLM 检测“它、这个方法、该论文、刚才那个”等指代，优先从 SQLite 结构化记忆中的活跃论文和主题提取候选：唯一候选自动补全并记录 original/resolved query，多候选或零候选返回明确澄清问题并以零 Token、零检索短路。pending query、候选和指代表达写入现有 SQLite checkpoint；下一轮用户回复候选名称或序号后恢复原问题、替换指代并继续研究流程，完整新问题则可放弃旧等待。服务响应暴露澄清状态和解析轨迹，澄清轮不更新研究主题或发布 Wiki。节点、主图、结构化记忆、Checkpointer 和测试目录代表性回归 19/19 通过。当前 v1 采用确定性中文指代表，不调用 LLM 做开放式共指消解；后续根据真实误判再决定是否增加低置信度模型辅助。

2026-08-14 已完成有界 Research Scheduler 与请求级 Evidence Store v1。有效 L3 Research Plan 会被编译为最多 2 个任务一组的依赖波次；未知依赖或循环依赖返回 `blocked_dependencies`，不会形成无限 Agent Loop。检索完成后，Evidence Store 以来源与定位符生成稳定证据 ID，对重复论文去重，保留标题、来源、页码/Chunk/DOI/URL、摘要片段、分数和关联任务，并为综合任务生成 Claim–Evidence 输入。L1/L2 不启用这两个节点，保持快速路径。运行指标与服务响应新增波次数、最大并行数、证据数及综合证据覆盖信息；5 个新增测试已进入中文测试目录，完整离线回归 288/288 通过，未调用真实 LLM。边界说明：v1 的任务—证据关联仍是词项重合启发式，Scheduler 已编译依赖与并发上限，但现有检索执行器仍负责实际串/并行；当前还没有逐声明 Coverage Gate，也不能把它描述为完整 Deep Research。下一步实现 Evidence Coverage Gate + Research Writer，使缺少证据的声明主动降级，并输出带稳定引用的结构化研究报告。

2026-08-14 已完成 Evidence Coverage Gate + Research Writer v1。Evidence Store 现在按综合任务依赖检查每个检索任务是否获得证据，不再以“至少有一篇论文”冒充完整覆盖；Coverage Gate 输出 `passed / partial / blocked / not_applicable`、覆盖率、未覆盖声明和缺失任务。`passed` 正常生成，`partial` 允许使用已有证据但强制标注缺失内容，`blocked` 以零 LLM 返回中文降级报告。L3 Research Writer 复用现有一次生成调用，把稳定 Evidence ID、标题、来源、定位符和片段注入科研 Skill Prompt，强制重要事实使用 `[E-...]`、禁止虚构引用、区分论文事实与综合判断，并在末尾生成证据索引；L1/L2 路径不变。服务响应和 metrics 暴露覆盖状态、覆盖率及 Writer 是否放行。6 个新增测试均进入中文测试目录，完整离线回归 294/294 通过，未调用真实模型。当前门控验证的是任务级证据可用性，还没有验证生成答案中的每个 `[E-...]` 是否存在、引用是否真正支持相邻声明；下一步建立小型端到端研究报告集，增加引用存在性、引用覆盖率和人工证据支持度评测，再决定是否增加一次受限 Writer Reflection。

2026-08-14 已建立小型研究报告端到端评测集 v1。冻结 4 个代表案例：ReAct/Reflexion Agent Loop 综述、RAG/GraphRAG 比较、ReAct 单论文批判和反思型 Agent 反馈—记忆分析；每项关键声明由人工指定允许的 Evidence ID。评测器计算引用存在率、虚构引用数、声明邻近引用覆盖率、中文结构完整率以及 LLM 调用/Token，并输出 JSON 与可由 Excel 直接查看的 CSV。默认命令只评测人工参考报告，用于验证 Harness，结果 4/4、各自动指标 100%、0 LLM、0 Token，明确不作为模型成绩；添加 `--confirm-online` 才运行约 4 次真实 Research Writer 调用并形成模型基线。相关 4 个单测通过。下一步运行一次真实模型基线，人工复核自动判分无法确认的“引用是否真正支持声明”，再根据失败类型决定修 Prompt、增加 Citation Validator，或启用最多一次 Writer Reflection。

2026-08-14 已完成首轮真实 Research Writer 基线。沙箱内首次 4 次均为 `APIConnectionError`，不计能力失败；允许网络后 4 次全部成功，共 18,464 Token。初始 0/4 由章节别名过窄造成，评测器改为接受“方法比较/方法对比/Method Comparison”等合法等价标题，并把声明引用检查从整节收紧为同句/同 bullet；复用已有原文零费用重判后为 3/4（75%），引用存在率 100%、虚构引用 0、声明局部引用覆盖率 91.67%、结构完整率 100%。唯一自动失败为 Agent Loop 综述中的综合比较判断没有相邻 Evidence ID。人工证据支持评分为 3/4、3/4、2/4、4/4，均值 3.0/4（75%）；ReAct 批判报告仅凭一句证据推断“停留在理论构想且无法通过严格审查”，属于明显过度推断。下一步优先增加生成后 Citation Validator，并收紧 Paper Critique Prompt 的“材料缺失不等于论文缺陷”边界；暂不增加 Writer Reflection，因为当前失败类型可以先由确定性校验和一次生成内约束解决。

2026-08-14 已完成 Citation Validator v1 与 Paper Critique 证据边界收紧。LangGraph 主路径更新为 `Research Writer → Citation Validator → Answer Verify`；新节点零 LLM 检查稳定 Evidence ID 是否真实、证据索引是否存在、每条“综合判断”是否在同一行附有效证据，以及批判报告是否把材料缺失过度推断为论文/贡献本身缺陷。失败类型会合并到现有 Answer Verification，并进入服务响应与 metrics；在独立复测前明确禁止自动触发 Writer Reflection。Paper Critique Prompt 新增“输入材料没有提供不等于论文没有做”、只有证据明确展示缺陷才能列为论文弱点，否则归入材料局限。7 个新增用例覆盖合规报告、虚构 ID、跨 bullet 借用引用、过度批判、快速路径、Verifier 合并和 Prompt 边界；相关回归 26/26、完整离线回归 307/307 通过，0 LLM、0 Token。下一步只重跑 4 题 Research Writer 真实集一次，与首轮 75% 自动通过率和 75% 人工证据支持度比较；若明显改善，再考虑仅对 Citation Validator 判定为可修复且证据充分的失败启用最多一次 Reflection。

2026-08-14 已完成 Research Writer v2 真实复测。首轮四题中后两题出现 `APIConnectionError`，新增按 case 定向重跑与旧报告合并能力，只补跑失败题，不重复消耗成功题 Token；最终 4/4 Provider 成功、共 18,061 Token。复用原文接入生产 Citation Validator 并修正其对建议句、元说明和纯标题的误报后，自动报告与 Validator 均为 3/4：通过率 75%、引用存在率 100%、虚构引用 0、声明局部覆盖率 91.67%、结构完整率 100%。唯一共同失败为 Agent Loop 报告的一条综合比较没有相邻 Evidence ID。人工证据支持从 v1 的 3.0/4（75%）提升到 3.25/4（81.25%），其中 Paper Critique 从 2/4 提升到 3/4，已明确区分材料局限与论文缺陷，不再出现“无法通过审查”的过度断言。下一步不扩大数据集；只针对 `uncited_synthesis_claim` 做最小 A/B：优先尝试零 LLM 的安全引用补全，只有无法确定唯一证据集合时才允许一次受限 Writer Reflection。

2026-08-14 已完成零 LLM Citation Repair v1 与 v2 原文 A/B。修复器只在 Citation Validator 的唯一失败为 `uncited_synthesis_claim`，且该行明确出现 Evidence Store 中可唯一映射的论文标题时，在行末补全对应 Evidence ID；标题缺失、同名证据歧义或同时存在虚构 ID 等其他失败均不修改。LangGraph 路径更新为 `Writer → Citation Validator → Citation Repair → Answer Verify`，修复后立即重新验证并原子更新状态。复用 18,061 Token 的 v2 四份原文，唯一失败的 Agent Loop 综合比较明确包含 ReAct 与 Reflexion，安全补入两个 ID；自动通过与 Validator 通过均由 3/4 提升到 4/4，修复 1 题，Token 增量为 0，其余三题原文不变。评测器补充固定的“比较/对比/相较、差异/不同/区别”别名，避免合法表达误判。下一步暂不启用 Writer Reflection：先把该零成本修复作为默认生产路径，再整理当前阶段代码和能力报告；只有后续真实案例出现无标题但证据充分的漏引，才建立受限 Reflection A/B。

2026-08-14 已完成 Research Agent Web 演示台升级。现有 FastAPI 首页直接复用 `/chat` 已暴露的研究元数据，新增 L1/L2/L3、Skill、LLM/Token、LangGraph 节点链路、Research Plan、依赖执行波次、Evidence Store 与 Coverage/Citation/Repair 三层质量闸门，不增加后端状态或模型调用。新增冻结的零 API L3 示例轨迹，现场无网络、无检索源或无模型凭据时仍可展示完整研究闭环，页面明确标记未调用 API/模型，避免把 fixture 冒充实时结果。Node 语法、FastAPI 静态契约和真实浏览器 DOM/视觉检查通过，浏览器控制台无错误。下一步优先补充最小 Docker 与基础 CI，或先录制/整理简历演示脚本；不继续扩大研究级评测。

2026-08-14 已完成最小 Docker 与基础 GitHub Actions CI。运行镜像基于 Python 3.10 slim、使用非 root 用户、Uvicorn 监听 8000，并通过标准库请求 `/health`；`.dockerignore` 排除 `.env`、PDF、Dense 模型/索引、SQLite、Wiki、日志和评测产物，Compose 只在运行时挂载 `data/` 与 `logs/`。CI 在 master push/PR 上执行 Node 前端语法检查、显式关闭 LLM/Checkpoint 的确定性 Research Agent 核心测试和 Docker build，不配置模型 Secret、不运行在线检索、不下载 Dense 模型。README 增加状态徽章、Compose 启停和数据持久化说明。下一步只需验证本机实际镜像构建与容器健康状态，再整理提交；如本机 Docker Desktop/网络不可用，以 Dockerfile 静态检查和 GitHub CI 首次运行结果为准。

2026-08-15 已完成指定页 PDF OCR 两阶段管线与结构化视觉证据 v1。页面 PNG 只在显式开启后发送给 `qwen3.5-ocr`，OCR 的 JSON/纯文本输出统一归一化，并以文件名、页码、内容类型、字符数和模型形成不含本地绝对路径的证据记录；主模型 `qwen3.7-max-2026-05-17` 再结合页面文本综合回答。OCR 成功而综合失败时保留提取结果并进入 `ocr_only_degraded`，不会丢弃第一阶段成果。当前内容类型是可审计的轻量标记识别，不等同于精确版面区域检测；下一步只增加 Figure/Table/Formula 三类受限 Skill 路由，不做整篇 PDF 自动扫描。

2026-08-15 已完成 Figure/Table/Formula 三类 PDF 子 Skill 路由。路由只检查用户明确表达，不调用额外 LLM：公式、方程、损失函数和符号进入 `FormulaExplanationSkill`，实验表格、指标和消融进入 `TableAnalysisSkill`，架构图、流程图和示意图进入 `FigureUnderstandingSkill`，其余请求保持 `PDFReadingSkill`。三类 Prompt 分别约束符号定义、数值比较和视觉关系，并继承 PDF 不可信证据边界；视觉状态不是 `used` 时不得声称观察到布局。下一步补一个不调用模型的 PDF Grounding Validator，检查专项回答是否披露页码、证据模式与识别不确定性，不扩大多模态评测集。

2026-08-15 已完成 PDF Grounding Validator v1。主图在生成与 Citation Repair 后、Answer Verify 前新增零 LLM 审计节点，只对 Figure/Table/Formula 专项回答启用：指定页必须全部出现，回答必须披露 OCR/视觉或仅文本证据模式，OCR 材料含无法识别、不清晰或未定义信号时必须保留不确定性。失败合并进 Answer Verification 并限制分数，但明确 `should_reflect=false`，不会为证据披露格式开启新循环。服务响应、Metrics、网页轨迹和冻结 PDF 示例均展示验证状态。下一步结束多模态 PDF v1 的连续开发，回到原计划中尚未完成且简历价值较高的 Structured Output，先为三类 PDF 专项回答定义轻量 Pydantic 结果契约，不做在线大规模评测。

2026-08-15 已完成 PDF Structured Output v1。Figure、Table、Formula 分别使用严格 Pydantic 契约描述组件关系、指标比较和符号定义，并共享最多 3 页的 Evidence Scope、`text_only / ocr_visual` 证据模式与不确定性列表。专项 Prompt 在中文答案末尾附机器 JSON；解析器移除该块后返回可读答案，校验成功的数据进入 `pdf_structured_output`，页码或模式与真实 State 不一致、额外字段、非法枚举及缺失 JSON 均记录为 `invalid`。当前主模型不支持原生结构化输出，因此失败保持中文回答并继续流程，不触发额外调用。下一步只做一条 Fake LLM 端到端图路径验证和一条受保护在线冒烟，再决定是否晋升为简历演示默认能力。

2026-08-15 已完成 PDF Structured Output 首次在线审计。沙箱内首轮为 0 Token 的 `APIConnectionError`，允许网络后 `qwen3.5-ocr → qwen3.7-max-2026-05-17` 两次调用均成功，共 8,215 Token、约 16.63 秒，Figure Skill 与 PDF Grounding 通过。Structured Output 唯一失败是第 3 页实际没有架构图，模型诚实返回空组件，而初版 Schema 强制至少一个组件；这属于契约误阻断，不计模型格式失败。契约现增加 `target_found`：发现目标图时必须有组件，未发现时允许空组件但必须写入 uncertainties；Prompt 示例页码也由固定 3 改为当前 State 页码。通过本地文本定位确认 Figure 1 GraphRAG Pipeline 位于 PDF 第 4 页，受保护冒烟默认页已纠正；按轻量评测原则本轮不重复付费调用。下一步结束多模态连续开发，回到整体路线中更有展示价值的阶段能力。

2026-08-15 已完成轻量 Multi-Agent v1 的结构化角色编排。没有新增三套重复模型调用，而是将现有 L3 Research Graph 映射为 Planner（Analysis/Brief/Plan/Schedule）、Executor（Tool/Retrieval/Evidence/Coverage）和 Reviewer（Citation/Repair/Grounding/Answer Verify）；三段使用严格 Pydantic Handoff 与总 Trace 契约，按顺序记录 completed/partial/blocked、输入引用、输出摘要和失败原因。只有 L3 启用，L1/L2 为 `not_applicable`；Review 上限 1，实际复用已有 Answer Reflection 次数，Orchestrator 额外 LLM 调用为 0。主图在 Answer Verify 最终停止后生成交接轨迹，服务、Metrics 和 Web 冻结示例均可展示。当前是同一 Research Graph 内的角色化协作，不是多个自治模型并行辩论。下一步只补一个代表性 L3 主图集成用例和简历能力说明，不进入分层八角色 Multi-Agent。

2026-08-15 已完成 PDF Grounding Validator v1。主图在生成与 Citation Repair 后、Answer Verify 前新增零 LLM 审计节点，只对 Figure/Table/Formula 专项回答启用：指定页必须全部出现，回答必须披露 OCR/视觉或仅文本证据模式，OCR 材料含无法识别、不清晰或未定义信号时必须保留不确定性。失败合并进 Answer Verification 并限制分数，但明确 `should_reflect=false`，不会为证据披露格式开启新循环。服务响应、Metrics、网页轨迹和冻结 PDF 示例均展示验证状态。下一步结束多模态 PDF v1 的连续开发，回到原计划中尚未完成且简历价值较高的 Structured Output，先为三类 PDF 专项回答定义轻量 Pydantic 结果契约，不做在线大规模评测。

2026-08-12 子查询并行已完成 5 次确定性离线重复基准：3 个子查询、2 个 worker 时，中位延迟由 265.4ms 降至 172.3ms，加速 1.54 倍、延迟下降 35.09%，结果与规划顺序一致率 100%，达到阶段门槛并收口。

随后已开始 Retrieval Replan v1：现有“低分后只扩大结果数”的普通重试升级为可审计的失败分类与受限动作。暂时工具失败保持原查询，零结果放宽字面限制，有结果但低相关时追加综述上下文；新查询覆盖旧子查询计划，仍受最多重试一次约束，全程不增加 LLM 调用或付费工具。下一步评测 Replan 相对普通重试的恢复率、无效重试率和动作分类准确率。
