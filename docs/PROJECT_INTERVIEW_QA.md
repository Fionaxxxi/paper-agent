# PaperAgent 项目面试题完整回答

更新日期：2026-08-23
使用原则：只回答 PaperAgent 已实现或与其技术选型直接相关的问题。电商、游戏平台、Redis Stream、Coding Agent、文件协同编辑、Hermes 自进化、Agentic RL、OpenClaw/Claude Code 源码等项目未涉及内容不写入本题库，避免把知识了解包装成项目经验。

回答口径分为两类：

- **项目实答**：当前代码已经实现，可以结合代码、测试或运行数据说明。
- **边界说明**：与项目相关，但当前只实现了有限版本；明确说明没有做什么，以及正式生产化应怎样扩展。

# 一、Agent 架构与多智能体设计

## 1. 你的 Agent 整体采用什么架构？是否基于 LangGraph 二次封装？梳理完整执行链路

PaperAgent 采用“FastAPI 服务层 + LangGraph 状态图 + Tool/MCP 治理层 + Retrieval/Evidence 层 + Skill/Verification 层”的分层架构。它不是重新开发一个 LangGraph，而是在 LangGraph 的 `StateGraph`、Conditional Edges 和 Checkpointer 上封装科研任务状态、节点计时、检索策略、证据契约和失败恢复。

完整执行链为：

```text
Web / API / CLI
→ PaperAgentService
→ 初始化 trace_id、user_id、conversation_id、PDF、会话上下文
→ 构造 AgentState
→ Intent Router
→ Clarification
→ Research Analyzer（L1/L2/L3）
→ Memory Retrieval
→ Query Rewrite
→ PDF 任务短路，或进入 Query Plan
→ Research Scheduler
→ Retrieval Router
→ Retrieve
   → Tool Router → Registry → Policy → Executor
   → Online / Personal / Local / Hybrid
→ Repository Enrichment（按需）
→ Evidence Store
→ Research Coverage
→ Evaluate
→ Retrieval Replan（最多一次）
→ Reason / Skill Router
→ Generate / Research Writer
→ Citation Validator
→ Citation Repair
→ Claim-Evidence Validator
→ PDF Grounding Validator
→ Answer Verifier
→ Answer Reflection（最多一次）
→ Memory Write Gate
→ Multi-Agent Finalize
→ Metrics / Trace / Stop Reason
→ 中文答案、证据列表和 Word/PDF 报告
```

LangGraph 的价值是将每个决策变成显式节点与边。节点只通过 `AgentState` 交换数据，因此检索、生成、验证和恢复可以独立测试，不需要把所有逻辑藏在一个 Prompt 里。

## 2. 架构选用 Master + Sub Agent 集群，还是固定 Workflow 流水线？

项目主体是**固定但带条件分支的 LangGraph Workflow**，L3 任务增加 Planner、Executor、Reviewer 三段有界角色协作，不是 Master 带多个常驻自治 Sub Agent 的集群。

选择原因：

- 论文研究任务的关键步骤相对稳定：理解、规划、检索、证据、生成、验证。
- 引用验证、权限检查、重试预算必须由代码保证，不能交给模型自由决定。
- 固定工作流更容易复现 Badcase、统计节点准确率和定位责任模块。
- 当前是简历项目，自治 Agent 集群带来的通信、调度和成本复杂度高于实际收益。

因此准确表述是：**Workflow-first，复杂任务使用 bounded multi-agent roles，而不是 autonomous agent swarm。**

## 3. 详细拆解一个复杂度最高的 Multi-Agent 落地项目，说明分工、路由逻辑与业务最终收益

项目中复杂度最高的是 L3 Research Flow，例如：

> 分析 Agent Memory 的主要架构、代表论文、工程实现和未来研究方向。

分工如下：

1. Planner：读取 Research Analyzer 输出，形成 Research Brief、子任务、依赖 DAG 和执行波次。
2. Executor：按照 Scheduler 的波次执行 Online/Personal/Hybrid 检索和可选 GitHub MCP，把结果写入 Evidence Store。
3. Reviewer：检查 Coverage、Citation、Claim-Evidence、PDF Grounding 和 Answer Verification，决定通过、修复或安全降级。

路由逻辑：

- Research Analyzer 根据目标数、比较维度、证据种类、时效性和开放程度判为 L3。
- Plan Validator 检查任务 ID、依赖存在性、无环和任务上限。
- Scheduler 只并行无依赖任务，当前最大并发由配置限制。
- Coverage 不足且 `retry_count=0` 时进入一次定向 Replan。
- Answer Verification 未通过且属于可修复失败、已有足够证据时进入一次 Reflection。

最终收益：复杂问题不再是“一次搜索 + 一次生成”，而是形成可审计的研究闭环；用户可以看到任务计划、证据来源、引用支持率、工具耗时和停止原因。当前 Multi-Agent 汇总额外 LLM 调用为 0，避免为了展示多 Agent 额外消耗 Token。

## 4. 部分模块为何采用 Workflow 固定流程 + 单点独立 Agent 组合，而不全量交由多智能体自主决策？

因为不同决策的风险不同：

- 权限、输入校验、超时、最大重试、数据隔离适合确定性代码。
- 研究目标理解、开放问题拆解、论文综合适合 LLM。
- 引用是否合法、Evidence ID 是否存在可以确定性检查。
- 声明是否被证据支持需要语义判断，但输出必须受结构化契约约束。

如果全部交给多 Agent，自主角色可能重复检索、互相放大错误、产生循环，并且难以回答“为什么调用了这个工具”。项目因此使用固定骨架约束边界，只在 Research Analyzer、Planner、Writer 和必要的语义验证点使用模型能力。

## 5. 用户首次提问、多轮补充、修改诉求三种场景，如何做任务路由、会话状态复用、断点续跑？

首次提问：

- 没有 `conversation_id` 时使用 `trace_id` 创建新会话。
- 初始化空历史和新 AgentState，从 Intent Router 开始。

多轮补充：

- 客户端继续传同一个 `conversation_id`。
- 服务从 SQLite 加载最近 6 条消息、旧消息摘要、活跃主题和论文。
- Clarification 使用历史解析“第二篇”“那个反思方法”等指代。
- LangGraph 使用 `thread_id=conversation_id` 读取官方 SqliteSaver Checkpoint。

修改诉求：

- 新消息作为新请求进入，不直接改写旧答案。
- `original_query` 保存原始输入，`resolved_query` 保存结合上下文后的真实任务。
- 如果“把刚才结论缩短”属于一次性改写，不写长期记忆；如果是新的研究目标，则重新分析复杂度和检索需求。

断点续跑：当前最完整的恢复场景是澄清恢复。系统保存 `pending_clarification`，用户补充后重新进入 Clarification 并继续。Checkpointer 能保存图状态，但项目没有实现面向分布式长任务的任意节点 Resume API，因此不能声称已经支持跨机器、精确一次的长任务续跑。

## 7. Agent 整体执行链路

面试中用以下四段回答最清晰：

1. 理解：Intent → Clarification → Research Analyzer。
2. 计划与执行：Rewrite → Plan → Schedule → Route → Tool/RAG。
3. 证据与生成：Evidence Store → Coverage/Evaluate → Skill → Writer。
4. 验证与治理：Citation/Claim/Grounding/Answer → Reflection → Memory Gate → Metrics。

简单问候在第一段结束；PDF 任务跳过第二段的在线检索；L3 才启用完整计划和角色交接。

## 8. execCtx 如何设计？

项目没有名为 `execCtx` 的独立类，对应概念由 `AgentState + LangGraph config + PaperAgentService` 共同承担。

执行上下文分为：

- 身份：`trace_id`、`conversation_id`、`user_id`。
- 输入：`query`、`pdf_path`、`retrieval_scope`。
- 计划：`task_level`、`research_plan`、`research_schedule`。
- 执行：`documents`、`tools_used`、`retry_count`。
- 质量：Coverage、Citation、Claim、Grounding、Answer Verification。
- 成本：`llm_usage`、Token、`node_timings`。
- 持久化配置：`configurable.thread_id=conversation_id`。

这样每个节点接收同一个状态快照并返回增量字段，避免依赖进程级可变全局上下文。

## 12. Checkpoint 如何设计？

项目使用官方 `langgraph-checkpoint-sqlite` 的 `SqliteSaver`：

- 数据库：`data/memory/langgraph_checkpoints.db`。
- 分区键：`thread_id=conversation_id`。
- SQLite 开启 WAL，允许读写并发性优于默认日志模式。
- 单例 Checkpointer 由锁保护初始化，应用退出时关闭连接。
- 支持按 `thread_id` 清理 `checkpoint_writes`、`checkpoint_blobs` 和 `checkpoints`。

除此之外，业务层还有独立 `pending_clarification` Checkpoint，用于在用户补充信息后恢复未完成澄清。两者分开是因为一个是 LangGraph 内部状态，一个是明确的业务恢复点。

## 13. 续跑状态机如何设计？

当前状态机依靠三个要素：

- `conversation_id/thread_id` 找到历史图状态；
- AgentState 中的 `retry_count`、`answer_reflection_count` 和质量状态防止重复循环；
- `pending_clarification` 标记任务为何暂停、需要用户补什么。

续跑时不是把整段旧对话重新当新任务，而是加载会话上下文和 Checkpoint，再根据当前状态进入允许的后继节点。检索和 Reflection 均有预算字段，因此恢复不会把次数清零造成无限重试。

## 14. Resume 执行流程如何保证一致性？

当前项目通过以下方式保证单机一致性：

- 同一会话始终使用相同 `thread_id`。
- Checkpoint 与业务消息都落 SQLite，而不是只存在内存。
- SQLite 使用事务和 WAL。
- 重试、Reflection 次数写入 AgentState。
- 工具结果使用统一契约，失败状态显式记录。

边界是：当前没有分布式任务队列、幂等键和 exactly-once Tool Commit，因此对有外部副作用的长任务不能声称实现了严格一次执行。当前工具主要是只读检索，这降低了 Resume 重复执行的风险。

## 15. Agent 内的中间件链如何设计？

项目没有通用 HTTP 风格 Agent Middleware 接口，但有两条等价治理链：

节点链：`timed_node → 业务节点 → AgentState 增量 → Metrics`，统一记录节点耗时。

工具链：

```text
Tool Router
→ Tool Registry
→ Tool Policy
→ Pydantic Input Validation
→ Timeout / Retry Executor
→ Pydantic Output Validation
→ ToolResult / Audit Metadata
```

如果后续抽象 Middleware，最适合提取的是 tracing、权限、预算、超时、重试、脱敏和错误标准化，而不是把业务规划逻辑做成中间件。

## 21. 如何设计 Multi-Agent 拓扑？

项目采用有向无环的角色拓扑：

```text
Planner
→ Executor
→ Reviewer
```

Planner 不执行工具；Executor 不决定最终答案是否可信；Reviewer 不重新规划所有任务。任务内部通过 Research Schedule 形成依赖 DAG，无依赖检索可并行，综合任务等待上游证据完成。

拓扑设计原则：按责任和数据契约划分，而不是按“角色名字是否丰富”划分；每个角色必须有明确输入、输出和停止条件。

## 22. 子 Agent 之间的通信如何实现？

当前不是 Agent 之间自由聊天，而是通过结构化 AgentState 通信：

- Planner 写 `research_brief/research_plan/research_schedule`。
- Executor 写 `documents/evidence_store/research_coverage/tool_executions`。
- Reviewer 写各验证结果和 `answer_stop_reason`。
- `multi_agent_finalize` 汇总成 `multi_agent_trace`。

这种方式比共享自然语言 MessageList 更稳定，因为下游读取的是 Pydantic/字典字段，而不是从长对话中猜测上游结论。

## 24. 如何理解 ReAct 中的 Loop？

ReAct 的核心是：模型产生 Thought/Action，执行工具获得 Observation，再根据新观察决定下一步，直到完成或达到停止条件。

PaperAgent 没有实现无限 ReAct Loop，而是把有价值的循环拆成两个有界闭环：

- Retrieval Loop：Evaluate → Replan → Retrieve，最多一次。
- Answer Loop：Answer Verify → Reflection → Verify，最多一次。

原因是研究检索容易出现路径震荡。显式预算和失败类型比让模型自行决定“继续思考”更容易控制成本和复现问题。

## 25. ReAct 中如何做异步？

项目的异步思想体现在独立任务并行，而不是并行 Thought：

- 多个独立子查询使用受限线程池并行检索。
- Personal 与 Online Hybrid 两个分支并行。
- 多论文源在开关启用后可受限并行。
- 有依赖的综合任务必须等待上游完成。

当前 FastAPI 业务调用仍以同步图执行为主，不是基于异步队列的后台 Agent。对分钟级任务，正式方案应使用任务队列、Job ID、事件流和可取消 Worker，而不是让 HTTP 请求一直占用连接。

## 26. 用户请求调用工具要跑半个小时，如何处理长耗时工具？

当前 Tool Executor 为每个工具定义超时和有限重试，适合秒级论文检索，不允许工具无限占用请求。半小时工具超出当前同步执行模型。

生产改造应是：

```text
POST 创建 Job
→ 返回 job_id
→ Worker 执行长任务
→ 持久化进度、心跳和 Checkpoint
→ SSE/WebSocket/轮询读取状态
→ 完成后将结果写入 Evidence Store
```

还必须提供幂等键、取消、超时、租约续期和失败重试。不能简单把 Tool Executor 的 timeout 调到 1800 秒，否则会占用 Web Worker，并且断线后难以恢复。

## 27. 模型返回很大的 JSON 串，局限性是什么？

- 占用大量输出 Token，增加成本和延迟。
- 长 JSON 更容易截断，导致无法解析。
- Schema 越复杂，字段遗漏和类型错误概率越高。
- 重复原文会挤占真正推理空间。
- 下游全量反序列化会增加内存和日志体积。

PaperAgent 的处理方式是限制 Top-K、截断文档正文、拆分状态字段，并用 Pydantic 校验 Research Analysis、Memory Metadata 和 PDF Visual Contract。生产中还可改为 JSONL/分页、对象存储引用或只返回 Evidence ID，不把大对象全部塞入模型上下文。

## 29. 如果子 Agent 调用长时工具，怎么通信合适？

当前项目工具是同步短任务。若扩展长时工具，子 Agent 不应持续向主 Agent 发送整段对话，而应发布结构化事件：`job_started/progress/evidence_ready/failed/completed`，事件包含 `trace_id`、`task_id`、序号和 Checkpoint 版本。主 Agent只消费状态和最终 Evidence 引用。

这属于合理扩展方案，不是当前已经实现的 Redis Stream 能力。

## 30. 主 Agent 如何拿到子 Agent 对话信息和进度？

当前通过共享 AgentState，而不是读取子 Agent 私有聊天：

- `research_schedule` 表示待执行任务和 Wave。
- `tool_executions` 表示工具执行结果。
- `evidence_store` 表示已产生证据。
- `multi_agent_trace` 表示 Planner/Executor/Reviewer 状态。
- `node_timings` 表示各节点耗时。

网页直接渲染这些字段，因此进度可解释且不依赖解析自然语言日志。

## 31. 工具在会话中的隔离是怎么做的？

工具定义和 Registry 可以全局共享，但用户数据不能全局共享：

- Online Search 是无用户状态的只读工具。
- Personal Library 查询必须传 `user_id`，SQL/检索层按 Owner 过滤。
- 会话历史与 Checkpoint 使用 `conversation_id` 分区。
- 工具输出写回当前请求的 AgentState，不写入共享可变列表。
- 工具缓存只缓存公开检索结果或模型索引，不缓存跨用户私有回答。

## 32. 多个 Session 调用一个全局变量会不会有问题？

如果全局变量可变且保存请求状态，会发生串话、覆盖和竞态。项目允许全局复用的对象仅限：

- 只读 Tool Registry/Router；
- 模型和本地索引缓存；
- 受锁保护的 Checkpointer 生命周期对象。

会话内容、文档、答案和计数都在 AgentState 或 SQLite 中按 ID 隔离。`SQLiteMemoryStore` 每次操作创建独立连接，避免 Web 请求共享 Cursor。

## 33. Session ID 传进去会有什么问题？

风险包括：客户端伪造别人的 Session ID、ID 冲突、路径注入、无限创建导致存储膨胀，以及只按 Session 不按 User 隔离造成越权。

当前项目以 `conversation_id` 作为 Checkpoint 键，Personal Library 另用 `user_id` 做 Owner 过滤。正式生产还应验证 Session 所属用户、限制长度与字符集、生成服务端不可预测 ID，并设置过期和清理策略。

## 34. Tool 不考虑 Session 可以吗？

无状态公共工具可以，例如 arXiv 搜索、日期时间和公开元数据查询。访问用户数据或会改变任务状态的工具不可以，例如个人论文库、记忆删除和报告资产管理。

判断标准不是“工具是否叫 Tool”，而是它是否读取私有状态、产生副作用或需要幂等语义。

## 35. 从代码耦合角度分析 Tool 的隔离设计

PaperAgent 用以下方式解耦：

- 节点只向 Tool Router 请求“能力 + 来源”。
- Router 返回注册名称，不依赖具体客户端类。
- Registry 保存 Tool Spec 和实现。
- Executor 只依赖统一输入/输出 Contract。
- Adapter 负责把 arXiv/OpenAlex 等外部格式转为统一论文结构。

因此替换 API 客户端通常只改 Adapter/Tool 注册，不需要修改 Planner、Evidence Store 和 Writer。MCP 工具与原生工具也能共用 Executor 治理。

## 36. 有什么办法让有状态 Tool 只执行一次？

当前检索工具是只读的，依靠缓存和一次重试预算减少重复调用。若是有副作用工具，应使用：

- `trace_id + task_id + tool_name + normalized_args` 生成幂等键；
- 执行前写入 pending 记录并使用唯一约束；
- 完成后保存结果引用；
- Resume 时先查幂等记录，成功则复用，pending 则检查租约，失败才按 Policy 重试。

这套 exactly-once 副作用机制当前没有完整落地，因此面试中应作为改进方案回答。

## 37. Skill 的自进化是否有了解？项目采用什么自进化方案？

PaperAgent 当前实现的是“基于评测反馈的受控策略进化”，不是 Hermes 式运行中自动生成并安装 Skill，也不是模型权重自训练。

流程为：Eval/Trace 生成 Failure Dataset，按责任模块归因；Candidate Generator 只从 Allowlist 提出 Prompt、Few-shot、Policy、Retrieval 或 Routing 候选；候选必须在同一冻结测试集生成 Baseline/Candidate Scorecard；Promotion Gate 要求总体质量至少提升 2 个百分点、逐题零回归、Critical/Safety 零退化、Provider Failure 不增加、Token 增幅不超过 10%、P95 延迟增幅不超过 15%；通过后只登记为 `eligible_for_human_approval`，不会自动修改 active version。

Hermes 类自进化更强调 Agent 从轨迹中生成或改写可复用 Skill。它的风险是错误 Skill 被自我强化、权限扩大和回归不可控。PaperAgent 更适合先演进策略和配置，因为已有完整 Eval、Trace 和证据验证基础。未来如果增加 Skill 生成，也必须经过 Schema 校验、隔离执行、冻结集回归和人工审批。

## 38. 平时如何学习 Harness？

结合本项目，可以回答为：我把 Harness 理解为 Agent 外部的工程控制系统，不只是 Prompt。学习时会把能力拆成 Context、Tool、Memory、Policy、Recovery、Eval 和 Observability 七个部分，然后用可执行案例验证。

PaperAgent 的实践包括：Tool Policy、Pydantic Contract、有限 Replan/Reflection、Memory Write Gate、测试用例目录、离线基准、在线 LLM 评测、Token 和节点 Trace。重点是每增加能力就定义输入输出、失败类型和可回归指标，而不是只观察一两个 Demo。

## 39. 一个 Agent 由哪几个部分组成？常见 Agent 框架有哪些？

一个工程 Agent 至少包括：模型、Prompt/Policy、状态、规划器、工具、记忆、执行循环、验证器和可观测性。

PaperAgent 对应关系：

- 模型：百炼 OpenAI-compatible 主模型和视觉模型。
- 状态：AgentState + SqliteSaver。
- 规划：Research Analyzer/Planner/Scheduler。
- 工具：Router/Registry/Policy/Executor/MCP。
- 记忆：Conversation Memory + Long-Term Memory。
- 验证：Coverage/Citation/Claim/Grounding/Answer。
- 观测：Trace、Token、节点耗时和测试报告。

常见框架包括 LangGraph/LangChain、AutoGen、CrewAI、Semantic Kernel、LlamaIndex Workflows。PaperAgent 选择 LangGraph 是因为状态图和条件边适合需要明确恢复与验证的研究流程。

## 40. 讲一下 ReAct 和 Plan-and-Execute。什么情况用什么？其他 Planning 方式有哪些？

ReAct 是“思考—行动—观察”逐步交替，适合下一步高度依赖刚获得结果、路径无法预先确定的任务。缺点是容易循环、成本难预测。

Plan-and-Execute 先形成任务计划，再执行子任务，适合论文调研、比较和报告生成这类目标可以拆解、依赖关系明确的任务。缺点是初始计划可能不完整，因此需要有限 Replan。

PaperAgent 以 Plan-and-Execute 为主：L2/L3 先建计划和 Wave；只保留两类受限反馈循环。其他方式包括 Routing、Sequential Workflow、Parallel Fan-out/Fan-in、Tree/Graph Search、Hierarchical Planning 和 Reflection-based Planning。

## 41. 有 500 个 Tool 和 500 个 Skill，怎么高效加载和调用？

不能把 1000 份描述全部放入 Prompt。推荐分层召回：

```text
用户任务
→ 一级领域路由（论文/代码/数据/办公）
→ 根据 capability metadata 检索 Top-K Tool/Skill
→ Policy 按用户权限、数据范围和风险过滤
→ 小候选集交给规则或 LLM 选择
→ 加载完整 Schema/Skill 内容
→ 执行后记录成功率和选择反馈
```

工程措施包括：

- Registry 只保存元数据索引，Schema 按需加载。
- Tool 与 Skill 分开：Tool 是执行能力，Skill 是任务方法和输出契约。
- 使用 capability、provider、risk、latency、cost、version 标签做过滤。
- 常用能力做静态快速路由，长尾能力再语义召回。
- 对候选集评测 Recall@K、Tool Selection Accuracy 和无效调用率。

PaperAgent 已实现 Router/Registry/Policy 的小规模版本和按任务只加载一个主 Skill；500+ 规模的向量化能力目录尚未实现。

## 43. 单 Agent 和 Multi-Agent 有什么区别？

单 Agent 使用一个决策主体完成规划、工具和生成，状态简单、延迟低，但复杂任务的职责边界容易混合。Multi-Agent 把计划、执行、审查等职责分开，可并行和独立评估，但会增加通信、状态一致性和 Token 成本。

PaperAgent 采用中间方案：L1/L2 主要走单图节点；L3 用 Planner/Executor/Reviewer 角色视图，但共享结构化状态且额外 LLM 为 0。这样获得职责可解释性，同时避免自治 Agent 对话成本。

## 45. Multi-Agent 系统中，不同 Agent 之间应该如何划分职责？

按“决策责任和输出契约”划分，而不是按业务名词随意拆角色：

- Planner 只负责目标和任务 DAG。
- Executor 只负责执行计划、调用工具、收集证据。
- Reviewer 只负责覆盖、引用和答案质量。

每个角色应有唯一负责人、明确输入、结构化输出、可测指标和停止条件。两个角色如果读取相同信息、调用相同工具并产生相同输出，通常不值得拆分。

## 46. 多个子 Agent 之间如何通信和任务协作？

项目使用共享 AgentState + Task/Evidence ID，而不是互相发送长自然语言消息。Planner 产生 Task ID，Executor 让每条 Evidence 关联 Task ID，Reviewer 根据映射计算 Coverage 和支持率。并行任务通过 Scheduler Wave 协作，依赖任务只能消费已完成上游结果。

生产分布式版本可把相同契约映射为事件总线消息，但语义仍应是状态和产物引用，而不是自由聊天。

## 49. ReAct 模式和 Plan 模式有什么区别？分别适用于哪些场景？

ReAct 适合短路径、工具结果决定下一步的探索任务，例如不知道仓库结构时逐步搜索文件。Plan 模式适合多对象比较、文献综述和报告生成，因为可以预先定义双方检索、依赖与最终综合。

PaperAgent 默认不是纯 ReAct。简单任务走固定短路径；复杂研究走 Plan-and-Execute；检索或答案失败时才进入一次反馈修复。

## 50. Agent 出现路径反复、重复尝试等“路径震荡”，可能原因是什么？如何优化？

原因通常包括：停止条件不清、工具返回错误不结构化、计划没有进度状态、每轮 Prompt 看不到已尝试动作、检索评价不稳定、模型可以反复选择同一工具。

PaperAgent 的优化：

- `retry_count < 1` 和 `answer_reflection_count < 1` 硬预算。
- ToolResult 记录错误码、尝试次数和工具版本。
- Replan 记录旧查询、新查询和失败原因。
- 新答案分数未提升时恢复旧答案。
- Task ID、Evidence ID 和 Stop Reason 显式写入状态。
- Smalltalk、PDF 等场景直接短路无关节点。

# 二、上下文、记忆、状态管理

## 1. Agent 上下文越来越长，超过模型限制，通常有哪些处理方式？

常见方案是滑动窗口、摘要压缩、结构化状态抽取、按需 RAG 召回、文档 Top-K、分层记忆和大内容外部引用。

PaperAgent 当前组合为：最近 6 条原始消息 + 更早消息提取式摘要 + 结构化研究上下文，总会话上下文上限 2400 字符；长期记忆单独 Top-K=3、上限 3000 字符；论文正文按 Top-K 和单文档长度裁剪，不把整个知识库塞给模型。

## 2. 上下文压缩时保留哪些信息？如何判断哪些可以丢弃？

项目优先保留：

- 最近 6 条原始消息；
- 用户长期表达偏好；
- 当前研究主题；
- 当前关注论文；
- 更早对话的尾部提取式摘要。

可以降低优先级的是寒暄、重复内容、已完成的一次性改写和可重新检索的公开事实。当前压缩是确定性字符预算，不使用 LLM 判断，因此成本为 0，但语义摘要能力有限。

## 3. 如何避免 Context 压缩后忘记重要需求？

不要只保留一段自由文本摘要。PaperAgent 将用户偏好、活跃主题和论文分别存入 `research_context` 表，并在上下文构建时优先分配预算。最近消息保留原文，避免摘要改写最新约束。

长期稳定结论则经过 Memory Write Gate 写入 Long-Term Memory，未来按需检索。这样重要信息既不完全依赖短摘要，也不会每轮全量注入。

## 4. 一个完整的 Agent 记忆系统如何设计？包括哪些模块？

完整系统至少包括：

1. Memory Extraction：从对话和结果提取候选记忆。
2. Write Gate：价值、稳定性、时效和验证判断。
3. Store：按用户、会话、类型和版本持久化。
4. Dedup/Conflict：重复合并、冲突审计。
5. Need Detection：判断当前任务是否需要记忆。
6. Retrieval：Owner 过滤、相关度、Top-K 和预算。
7. Update/Expiry/Forget：更新版本、Snapshot 过期和隐私删除。

PaperAgent 已实现以上 v1：生成时产生 Metadata，代码 Gate 决定写入；SQLite 保存；召回时按需 Top-K；支持重复、冲突、Snapshot 过期和删除接口。

## 5. 当前对话 Context 和长期 Memory 有什么区别？

Context 是本次模型调用直接看到的工作区，解决当前轮理解问题；容量有限且随调用变化。Long-Term Memory 是持久化、可检索的历史研究知识，默认不直接进入 Prompt。

项目中：会话 Context 来自最近消息、旧摘要和研究状态；Long-Term Memory 保存经过验证的 Research Finding、用户研究主题等派生知识。论文原文属于 Personal Library，不属于 Long-Term Memory。

## 6. Memory 信息如何提取、存储和检索？

提取：L2/L3 生成答案时在同一次模型调用输出隐藏 Memory Metadata。  
判断：Memory Write Gate 检查验证结果、`value_score>=0.75`、稳定性、时效、重复和冲突。  
存储：写入 SQLite 长期记忆表，并绑定 Owner、主题、类型和版本。  
检索：显式历史请求或 L3 才触发，Owner 过滤后按相关度取 Top-3，排除失效 Snapshot，将上下文限制在 3000 字符。

## 7. 为什么一些记忆管理、上下文压缩可以交给小模型？

因为这类任务通常是分类、字段抽取和短摘要，不需要主模型完整推理能力，小模型成本和延迟更低。但 PaperAgent 当前没有单独部署记忆小模型：短期压缩使用确定性提取，Need Detection 和最终 Gate 使用代码，Metadata 由主生成调用顺带输出，因此不增加额外模型调用。

## 8. 短期记忆的具体实现方式是什么？

当前实现不是“接近模型 Token 上限时才压缩”，而是固定窗口策略：

- 所有消息保存在 SQLite `messages` 表。
- 每轮读取最近 6 条原文。
- 更早消息生成最多 1200 字符的提取式摘要。
- 偏好、主题和论文单独结构化保存。
- 最终拼装上下文限制为 2400 字符。

如果按一问一答计算，最近 6 条大约对应最近 3 轮，而不是最近 6 轮。

## 9. 什么叫“快到上限了”？对话怎么逐步叠加？

通用做法是统计模型 tokenizer 的输入 Token，当“系统 Prompt + 历史 + 工具 Schema + 文档 + 预留输出”达到窗口的 70%—85% 时触发压缩。

PaperAgent 当前没有 Token 动态触发器，而是每次加载时固定切分最近 6 条和更早消息，再按字符预算裁剪。优点是确定、0 LLM；缺点是字符数不如真实 Token 精确，这是后续可优化点。

## 10. 对话轮次过多怎么优化？

- 原始消息继续落 SQLite，不全量注入。
- 最近窗口保留原文。
- 旧消息压缩。
- 用户偏好、活跃主题和论文结构化抽取。
- 历史研究结论进入长期记忆并按需 Top-K。
- 过期 Snapshot 失效，支持会话删除。

当前项目已经采用这套分层方案，后续主要改进是把字符预算升级为 tokenizer 预算，并让旧摘要增量更新。

## 11. 什么时候触发总结动作？

当前每次 `load_context` 都把“最近 6 条之外”的消息做提取式压缩，但不调用 LLM。只要总消息数超过 6，就会出现 `older_summary`。

因此触发条件是消息数量超过窗口，而不是每轮都调用摘要模型。

## 12. 每一轮都要总结吗？

不需要。前 6 条以内没有旧摘要；超过后只在构建上下文时做廉价确定性压缩。长期记忆也不是每轮写入，只有 L2/L3 且验证和价值门槛通过才写。

## 13. 已进行 10 轮并做了总结，第 11 轮开始时怎么处理？

当前实现会从 SQLite 读取全部消息，重新划分“最近 6 条”和“更早消息”，再对更早部分生成提取式摘要，不是将第 11 轮机械追加到旧摘要。

这种实现简单一致，但会重复读取旧消息。大规模生产更适合保存滚动摘要版本：`旧摘要 + 新移出窗口的消息 → 新摘要`，同时保留摘要版本和来源范围。

## 14. 前 10 轮变成摘要后，原始上下文不需要了吗？

模型当前调用不需要全量原文，但存储层仍保留原始消息。这样可以审计、重新摘要、处理删除请求和恢复错误摘要。不能为了节省 Prompt 就立即删除所有原始记录。

## 15. 长期记忆在什么情况下需要检索？

PaperAgent 的触发条件是：

- 问题包含“基于之前、继续上次、上次结论、还记得”等显式信号；或
- 当前是 L3 复杂研究任务，历史结论可能帮助规划。

检索后仍要检查相关度、Owner 和时效。询问“最新论文”时不能只使用旧记忆，必须在线检索。

## 16. 每轮都注入记忆吗？长短记忆同时注入吗？

短期会话上下文每轮加载，因为它负责连贯对话；长期记忆不是每轮注入，只有 Need Detection 触发才召回。两者可以同时存在，但有独立预算：短期 2400 字符，长期最多 3000 字符。

普通问候和 L1 检索不会加载长期记忆，避免 Token 浪费和旧知识干扰。

## 17. 如何减少工具过多带来的 Token 消耗？

PaperAgent 不把所有工具 Schema 交给模型自由选择，而是先用确定性 Retrieval Router 和 Tool Router 根据“能力 + 来源”缩小到一个工具。Skill Router 同样只加载当前主 Skill。这样工具数量增长不会线性增加每次 Prompt。

# 三、工具、Skill、MCP

## 1. MCP 是什么？Agent 通过 MCP 调用工具的流程是什么？

MCP 是 Model Context Protocol，用统一协议描述工具、资源和调用契约，使工具不必与某个 Agent 框架强绑定。它不是检索算法，也不是多 Agent 必需协议。

PaperAgent 调用链：

```text
Planner/Retrieval 判断需要某种 capability
→ Tool Router 根据 capability + source 选择工具名
→ Tool Registry 取得 MCP-compatible Tool Spec
→ Tool Policy 检查权限和风险
→ Pydantic 校验输入
→ Tool Executor 执行超时和有限重试
→ 校验输出
→ 统一 ToolResult
→ 转换为 Document/Evidence
→ 写入 AgentState 和 Trace
```

当前 MCP 方向重点是 GitHub 和 Zotero；arXiv/OpenAlex 等也经过同一 Tool 治理层，但不要把所有 Adapter 都描述为外部官方 MCP Server。

## 2. 大量工具时如何避免工具描述导致 Prompt 过长？

- 先做领域/能力路由，再加载候选工具完整 Schema。
- Registry 保存简短索引元数据，详细说明延迟加载。
- Policy 先按权限、用户状态、风险和可用性过滤。
- 常用确定性意图直接映射，不调用 LLM 选工具。
- 只将 Top-K 候选交给模型处理长尾歧义。

PaperAgent 当前使用确定性 capability-to-tool 路由，因此通常不把工具描述塞入生成 Prompt。

## 3. 工具返回数据量过大，超过上下文窗口怎么办？

项目使用多级收缩：

- Retriever 侧限制每源结果数，Local 默认 5，多源合并默认最多 8。
- 去重后再 Top-K。
- 文档正文按 `DOC_CONTENT_LIMIT` 截断。
- Evidence Store 保存完整定位信息，Prompt 只放需要的摘要/片段。
- PDF 视觉最多选择 3 页。

更大规模时应将原始结果写对象存储，只在状态中保存引用、统计和 Evidence ID，并通过分页或二次检索按需读取。

## 4. 工具太多为什么容易选错？怎么解决？

因为描述语义相似、命名不稳定、权限和数据范围混在 Prompt 中，模型还可能忽略成本。解决办法是分层路由、结构化 capability、来源约束、候选 Top-K、Schema 校验、选择置信度和离线 Tool Selection Eval。

PaperAgent 将“检索范围”和“具体工具”分开：先决定 Online/Personal/Hybrid，再根据来源选择 arXiv/OpenAlex 等具体工具，减少一次决策承担过多语义。

## 5. 写过 Skill 吗？Skill 由几个部分组成？

PaperAgent 写了 QA、Summary、Compare、Literature Review、Trend、Limitation、Paper Ranking，以及 Figure/Table/Chart/Formula 等 Skill。

一个 Skill 至少包含：

1. 适用条件或任务类型。
2. Prompt 构造规则。
3. 所需输入字段和证据要求。
4. 输出格式或 Pydantic Contract。
5. 失败/降级策略。
6. Registry 名称和版本。
7. 对应测试用例。

Skill 与 Tool 的区别：Skill 决定“如何完成和表达任务”，Tool 负责“执行外部动作或获取数据”。

# 四、评测体系与 Badcase 迭代闭环

## 1. Agent 效果如何量化？自动化指标与人工抽检怎么组合？

不能只用最终答案准确率。PaperAgent 分层评测：

- Intent Router：意图准确率、Smalltalk 本地短路数、避免 LLM 调用数、研究问题误阻断数。
- Query Plan：计划准确率、查询数量、简单任务过度拆分数。
- Retrieval：Recall/命中、去重数、Coverage、比较双方覆盖、延迟和稳定性 CV。
- Tool：路由正确率、参数契约、超时/重试、错误分类。
- Generation：答案任务完成度、引用合法率、Claim 支持率、Grounding。
- Agent：最终通过率、Replan/Reflection 成功率、Token、总延迟和 Stop Reason。

自动化负责稳定回归；人工抽检负责判断开放研究结论、证据是否真正支持、表达是否有误导性。当前基线：完整离线回归 422/422；正式 LLM 核心集 29/30，通过率 96.67%，供应商失败 0；16 题最终回答 A/B 的内容质量分由 68.44 提升至 92.34。

## 3. 问题回流后，如何定位是 Agent、RAG、检索策略还是 Prompt？

根据 Trace 从前向后定位：

1. Intent/Clarification 错：看 `input_intent/resolved_query`。
2. 规划错：看 Research Analysis、子任务和 Plan Validation。
3. 工具错：看 Tool Route、参数、错误码和来源状态。
4. RAG 错：看实际召回 Chunk、Top-1、margin、Dense/Hybrid 路由和 Coverage。
5. 证据足但答案错：看 Skill Prompt、Citation 和 Claim-Evidence。
6. 修复后变差：看 Reflection 前后分数和是否恢复旧答案。

每个失败用 `trace_id` 关联，先确定最早出现错误的节点，避免一发现最终回答错就直接修改主 Prompt。

## 5. Prompt 修复一类问题导致另一类退化，如何规避？

项目采用 Prompt 版本和回归集，而不是直接覆盖生产 Prompt：

- Prompt Registry 记录名称、版本和结构化输出契约。
- Research Analyzer 有 zero-shot/few-shot 变体 A/B。
- 固定离线测试保证路由和契约不退化。
- 30 题在线 LLM 集检查真实模型表现。
- 对失败区分 Provider Failure 与 Capability Failure。

正式灰度应按 `prompt_version` 分流小比例请求，比较通过率、Token、延迟和关键分组指标，再决定晋升。当前项目有离线 A/B 和晋升门槛思想，但没有真实生产流量灰度平台。

## 7. Prompt 是人工迭代，还是有 A/B 和自动回归流水线？

两者都有，但规模有限：Prompt 由人工设计，测试集和脚本负责自动批量回归；Research Analyzer 已建立 zero-shot/few-shot A/B，LLM 在线评测支持一键运行和 JSON/CSV/Excel-ready 报告。CI 默认只跑离线确定性测试，避免每次提交产生模型费用。

在线评测不会每个阶段自动全量运行，而是在 Prompt、模型或语义路由发生重要变化时执行。

## 8. 怎么评测一个 Agent？为什么不能只看最终答案？

最终答案可能“碰巧正确”，但中间用了错误证据；也可能答案合理但成本和延迟不可接受。因此要同时评估：

- 任务路由是否正确；
- 计划是否有效；
- 工具选择和参数是否正确；
- 检索证据是否覆盖问题；
- 引用是否存在且支持声明；
- 恢复是否有效、是否发生震荡；
- Token、延迟、缓存和失败率；
- 最终答案的正确性、完整性和可读性。

PaperAgent 的 Evidence Store 和节点 Trace 正是为了让这些中间指标可观察。

# 五、RAG 相关

## 1. 你的 RAG 用什么技术实现？

项目级 Local RAG 使用：

- PyPDF 按页解析论文。
- Fixed Window Chunker 切分 Chunk。
- FastEmbed + `paraphrase-multilingual-mpnet-base-v2` 生成 Dense Embedding。
- NumPy/本地文件保存冻结向量缓存。
- BM25 提供关键词检索。
- RRF 融合 Dense 与 BM25。
- Confidence Gate 根据 Dense Top-1 和 margin 选择 Dense 或 Hybrid。

当前参数：Dense Top-1 高于 0.65 或 margin 高于 0.05 时倾向 Dense，否则执行 Hybrid；RRF `k=40`，候选上限 50。个人论文库 MVP 当前使用 Owner-scoped BM25，没有把项目级 Dense 索引直接复制到每个用户。

## 2. 如何判断向量相似度？

Dense Retriever 将查询和 Chunk 编码为向量，使用归一化向量的余弦相似度衡量方向接近程度。分数越高，语义越接近。

项目不仅看 Top-1，还看第一名与后续候选的分数间隔 `margin`：Top-1 高且间隔明显，说明 Dense 决策稳定；Top-1 或 margin 偏低时使用 BM25 + Dense 的 RRF，避免语义模型在低置信度下独断。

## 3. 除了余弦相似度，还了解哪些算法？

常见有欧几里得距离、点积、曼哈顿距离、Jaccard，以及检索融合中的 RRF。向量数据库还常用近似最近邻索引 HNSW、IVF 等加速搜索，它们是检索索引方法，不是新的语义相似度定义。

PaperAgent 实际 Dense 路径主要使用余弦相似度，词法路径使用 BM25，排序融合使用 RRF。

## 4. 余弦相似度与欧几里得距离在工程应用中的区别？

余弦关注向量方向，忽略模长；文本 Embedding 通常更关注语义方向。欧几里得关注空间中的绝对距离，受向量模长影响。

当向量都做 L2 归一化时，两者排序关系接近；未归一化时差异明显。文本检索通常使用归一化余弦或点积；聚类、几何位置和模长含义重要的特征可能更适合欧氏距离。项目选择余弦是因为使用的是语义文本 Embedding。

## 5. 项目一共使用几个模型？分别是什么？

生产主链路涉及三个模型角色：

1. `qwen3.7-max-2026-05-17`：主生成、复杂研究分析、必要的语义路由和答案修复。
2. `qwen3.5-ocr`：PDF 关键页视觉/OCR 理解。
3. `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`：本地 Dense Embedding，通过 FastEmbed/ONNX 运行。

评测历史中试验过 multilingual MiniLM，但当前 Local RAG 生产路径是 MPNet。规则路由、BM25、RRF、Coverage 和大多数验证不属于模型。

## 6. 如何控制模型幻觉？

PaperAgent 使用多层控制，不只依赖 Prompt：

- Retrieval Scope 防止用公开结果冒充个人库。
- Evidence Store 为来源分配 ID 和定位信息。
- Coverage 在生成前检查比较双方和必需任务是否有证据。
- Prompt 要求关键结论绑定 Evidence ID。
- Citation Validator 检查引用 ID 合法性。
- Claim-Evidence Validator 判断声明是否真正被证据支持。
- PDF Grounding 限制页面和视觉事实。
- Answer Verifier 做最终总检。
- 证据不足时最多定向补检一次，仍不足则明确降级。
- 验证未通过的结论不能写长期记忆。

## 7. 如何观察模型召回了哪些块？

每个 Local RAG 结果保留 `document_id`、`chunk_id`、页码、正文片段、来源和 `retrieval_score`。网页 Evidence Store 和检索证据面板展示这些信息，Trace 中还记录：

- Dense Top-1；
- 分数间隔 margin；
- 最终选择 Dense 还是 Hybrid；
- 原始、合并、去重后的文档数量；
- 查询、数据源和缓存命中。

因此可以从最终声明回到 Evidence ID，再回到具体 PDF 页和 Chunk。

# 六、缓存与性能

## 与项目相关的缓存设计

PaperAgent 当前没有实现模型供应商级 Prompt Cache，因此不把 Prompt Cache 作为已落地能力。已经实现的是：

- 在线论文检索结果缓存，重复查询减少外部 API 调用。
- Local RAG Dense 向量冻结缓存，避免每次启动重算论文 Embedding。
- FastEmbed 模型缓存固定在项目 `data/cache`。
- PDF 页面 PNG 缓存，重复视觉分析不重复渲染。
- 进程内 `lru_cache(maxsize=1)` 复用 Local Retriever。

提高命中率的方法是规范化查询、稳定缓存键、版本化模型/解析器/Chunker Fingerprint，并区分公开缓存与用户私有缓存。模型、Chunk 或解析器版本变化时必须生成新 Fingerprint，不能错误复用旧向量。

# 七、面试中应主动说明的未涉及范围

以下内容不要回答成 PaperAgent 项目经验：

- Redis Stream、Redis Pub/Sub 和游戏服务器通信；
- GET/Create 分布式竞态、读写锁死；
- 长任务事件总线和分布式 exactly-once；
- 多 Agent 同时修改文件与 MessageList Fork；
- 电商订单、价保、退款和优惠券业务；
- Coding Agent 沙箱和代码编辑系统；
- Agentic RL、SFT 子 Agent；
- OpenClaw 与 Claude Code 源码对比。

如果被追问，应明确回答：“这个项目没有落地该能力；与 PaperAgent 最接近的设计是……；如果生产化，我会采用……”。先说边界，再讲迁移方案，比把通用知识伪装成项目实现更可信。

# 八、项目面试总述

PaperAgent 最值得讲的不是“用了 LangGraph、RAG 和 MCP”这些名词，而是三个工程闭环：

1. **执行闭环**：复杂度分层、计划、工具、有限 Replan 和明确停止原因。
2. **证据闭环**：Evidence Store、Coverage、Citation、Claim、Grounding 和 Answer Verification。
3. **记忆闭环**：短期上下文、Checkpoint、按需长期召回、Write Gate、重复冲突和时效管理。

面试回答应始终落到具体状态字段、阈值、失败路径和测试数据：完整离线回归基线 422/422，正式 LLM 核心评测 29/30（96.67%）；16 题最终回答 A/B 中，不含引用因素的内容质量分由 68.44 提升至 92.34，证据不足披露率由 28.57% 提升至 100%；PDF Vision 和 Personal+Online Hybrid 均完成真实在线冒烟。这样能证明项目不是架构图堆叠，而是可运行、可验证、知道边界的 Agent Engineering 项目。
