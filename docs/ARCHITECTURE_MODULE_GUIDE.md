# PaperAgent 架构模块逐流程详解

更新日期：2026-08-23
说明：本文严格按照一次用户请求在系统中的实际流动顺序，解释架构中的每个模块。每节回答五个问题：模块为什么存在、接收什么、依据什么判断、产出什么、失败后如何处理。

## 1. 先理解整条主链路

```text
用户入口
→ PaperAgentService 服务编排
→ AgentState 初始化
→ Intent Router 意图路由
→ Clarification 澄清与上下文恢复
→ Research Analyzer 研究复杂度分析
→ Memory Retrieval 按需长期记忆召回
→ Query Rewrite 查询改写
→ Query Plan 任务拆分
→ Research Scheduler 依赖和执行波次
→ Retrieval Router 检索范围决策
→ Retrieve + Tool/MCP 执行
→ Repository Enrichment 可选代码证据
→ Evidence Store 证据规范化
→ Research Coverage 证据覆盖检查
→ Evaluate 检索质量评估
→ 必要时 Retrieval Replan，最多一次
→ Reason + Skill Router 能力选择
→ Generate / Research Writer 生成答案
→ Citation / Claim / PDF Grounding / Answer Verification
→ 必要时 Answer Reflection，最多一次
→ Memory Write Gate 长期记忆写入决策
→ Multi-Agent Finalize 角色交接汇总
→ Metrics / Trace / Stop Reason
→ 中文回答、证据、轨迹和 Word/PDF 报告
```

不是所有请求都会经过所有节点。问候会在 Intent Router 后结束；PDF 任务会跳过在线检索；只有复杂研究任务才启用完整 Research Plan、Coverage、长期记忆和 Multi-Agent 轨迹。

## 2. 用户层：请求从哪里进入

### 2.1 Web Research Console

Web Console 是给普通用户和面试演示使用的网页入口。

- 输入：研究问题、`conversation_id`、检索范围、可选 PDF 路径和页码、登录身份。
- 主要操作：注册登录、上传个人论文、选择 Personal/Online/Hybrid、发起研究、查看示例轨迹、下载报告。
- 输出展示：最终结论、论文列表、Research Plan、执行波次、Evidence Store、质量闸门、工具记录、Token 和节点耗时。
- 特点：网页本身不决定 Agent 如何推理，只负责收集参数并呈现服务端返回的结构化状态。

### 2.2 FastAPI / Swagger

FastAPI 是程序化服务入口，Swagger 是自动生成的接口调试页面。

- FastAPI：把 HTTP 请求映射到 Python 服务，定义 `/chat`、认证、论文库、记忆和报告导出等接口。
- Pydantic：在进入业务逻辑前校验字段类型、必填项和允许值，避免错误数据直接流入 LangGraph。
- Swagger：读取 FastAPI 的接口模型，生成可交互的 `/docs` 页面，不参与 Agent 推理。
- Uvicorn：实际监听端口并运行 FastAPI 应用，是网络服务器而不是业务模块。

### 2.3 CLI

CLI 是命令行入口，适合本地开发、最短路径调试和无前端运行。

- 输入和 Web 基本相同，但不负责网页渲染。
- 最终仍调用同一个 `PaperAgentService`，所以 CLI 和 Web 不应各自维护一套 Agent 逻辑。
- 它的价值是隔离前端问题：如果 CLI 正常、网页异常，通常说明故障在 API 或前端展示层。

## 3. PaperAgentService：业务请求总入口

`PaperAgentService` 位于用户入口和 LangGraph 之间。它不负责研究推理，而是为一次运行准备完整上下文。

### 3.1 Trace ID

- 每次请求生成唯一 `trace_id`。
- 节点耗时、工具调用、错误、LLM 用量和最终回答都通过它关联。
- 它解决“这条日志属于哪次请求”的问题，不能代替 `conversation_id`。

### 3.2 用户与会话身份

- `user_id`：决定个人论文、长期记忆等私有数据归谁所有。
- `conversation_id`：标识连续对话和 LangGraph Checkpoint 线程。
- 没有提供会话 ID 时，服务会使用本次 Trace ID 创建新会话。
- Personal Library 检索必须带 Owner 条件，不能先全库检索再在返回阶段过滤。

### 3.3 PDF 输入准备

当请求带有 `pdf_path` 时，服务在进入 LangGraph 前先处理文件：

```text
是否提供页码？
├─ 是 → 校验并使用指定的 1—3 页
└─ 否 → 本地检测是否存在图、表、曲线、公式意图
   ├─ 普通阅读 → 提取全文文本
   └─ 视觉问题 → 根据查询词和图注自动选择最多 3 页
```

- 文本路径：提取 PDF 文字并限制最大字符数。
- 视觉路径：将关键页渲染为 PNG，记录页码、图片路径和视觉状态。
- 自动选页是本地确定性逻辑，0 次 LLM；只有真正的视觉解析才发送选定页面。
- 文件不存在、解析失败或渲染器不可用时写入 `pdf_error`，系统可以降级为已有文本，而不是无提示崩溃。

### 3.4 会话记忆与 Checkpoint

这里有两种不同的数据：

- 会话记忆：消息写入 SQLite。读取时保留最近 6 条原始消息，并从更早的消息中确定性提取最多 1200 字符的摘要上下文，用于理解“它”“第二篇论文”等后续问题；当前并不是每轮额外调用 LLM 生成增量摘要。
- LangGraph Checkpoint：按 `conversation_id/thread_id` 保存图状态，服务重启后仍可恢复运行上下文。

构造模型输入时，系统再把结构化会话状态、早期摘要和最近消息放进约 2400 字符的上下文预算。早期原始消息仍保留在 SQLite 中，裁剪的是本轮模型输入，不是删除历史。Checkpoint 是流程状态恢复，不等于长期知识记忆；长期研究记忆在后面的 Memory 模块处理。

### 3.5 LangGraph State 初始化

服务将所有输入组装为 `AgentState`。它是整个工作流共享的状态对象，主要字段包括：

- 请求：`query`、`original_query`、`resolved_query`。
- 身份：`trace_id`、`conversation_id`、`user_id`。
- 规划：`task_level`、`research_brief`、`research_plan`、`research_schedule`。
- 检索：`retrieval_scope`、`sub_queries`、`documents`、`retrieval_score`。
- 证据：`evidence_store`、`research_coverage`、各类验证结果。
- 生成：`task_type`、`answer`、`memory_metadata`。
- 运行：`tools_used`、`llm_usage`、`node_timings`、`retry_count`。

每个 LangGraph 节点只读取自己需要的字段并返回增量更新，避免模块通过全局变量隐式耦合。

## 4. Intent Router：先判断请求是否值得进入 Agent 流程

### 4.1 目标

避免 `hi`、感谢、告别等简单输入也触发检索和大模型，从入口处控制 Token 与延迟。

### 4.2 判断逻辑

```text
用户问题
→ 规范化大小写和符号
→ 匹配 Smalltalk 模式
├─ 命中 → 本地模板回答，input_intent=smalltalk
└─ 未命中 → input_intent=research
```

- Smalltalk 主要使用规则判断，0 次 LLM。
- 规则必须尽量保守，避免把“hi 在论文中是什么意思”之类研究问题误判为问候。
- `research` 在这里表示“继续分析”，不代表已经决定是 L1、L2 或 L3。

### 4.3 输出和路由

- Smalltalk：直接写入 `answer` 并结束 LangGraph。
- Research：进入 Clarification。

## 5. Clarification：澄清与上下文恢复

### 5.1 目标

在规划和检索之前确定用户究竟在问什么，防止模糊指代污染后续所有节点。

### 5.2 三类处理

#### 明确指代：规则恢复

例如“第二篇”“上一个回答”“刚才的 ReAct 论文”。

- 从当前问题提取序号、标题或明显实体。
- 在最近消息、活跃论文和候选列表中查找。
- 唯一命中时生成 `resolved_query`，0 次 LLM。

#### 描述性指代：受限语义解析

例如“那个用反思记忆的方法”。

- 只有规则不能唯一恢复、同时又存在有限候选时，才允许语义模型判断。
- 模型只能在提供的候选集合中选择，不能凭空创建对象。
- 结果还要经过置信度和候选合法性 Policy。

#### 无法恢复：主动澄清

- 没有候选、序号越界或语义置信度不足时，设置 `clarification_required=true`。
- 系统返回具体澄清问题并暂停，不会带着猜测继续检索。
- 待用户补充后，通过会话保存的 `pending_clarification` 恢复任务。

## 6. Research Analyzer：判断研究复杂度

### 6.1 目标

决定任务需要多重的工作流，而不是所有问题都使用同一套昂贵流程。

### 6.2 主要分析字段

- `objective`：用户最终想得到什么。
- `question_type`：检索、总结、比较、趋势、批判或开放研究。
- `entities`：方法、论文、作者、年份和研究主题。
- `dimensions`：用户要求比较或分析的维度。
- `freshness`：是否需要最新资料。
- `evidence_need`：需要单篇、多篇、代码或本地材料。
- `complexity_score`：综合复杂度分数。

### 6.3 L1/L2/L3

- L1：单一目标、一次检索或直接 PDF 问答，例如“找三篇 RAG 论文”。
- L2：明确比较或多条件组合，例如“比较 GraphRAG 与 LightRAG 的索引和查询机制”。
- L3：开放研究、趋势判断、多来源综合或需要形成报告，例如“分析 Agent Memory 值得研究的方向并给出证据”。

规则特征负责提供稳定下限；复杂、模糊的研究意图可以使用一次结构化 LLM 分析。模型输出必须满足 Pydantic Contract，不合法时回退到规则结果。

## 7. Memory Retrieval：按需想起长期研究结论

### 7.1 触发条件

- 用户明确询问历史研究结论；或
- 当前任务为 L3，历史知识明显有复用价值。

普通 L1 问题默认不加载长期记忆，避免无关上下文增加 Token。

### 7.2 召回逻辑

```text
Need Detection（代码 Policy）
→ 按 user/conversation Owner 过滤
→ 排除过期或失效 Snapshot
→ 相关度排序和 Top-K
→ 上下文长度裁剪
→ long_term_memory_context
```

长期记忆是过去验证过的“派生研究结论”，不能冒充当前检索证据；时效性问题仍必须重新在线检索。

## 8. Query Rewrite：把自然语言改成适合检索的查询

### 8.1 目标

保留用户真实研究意图，同时去掉对搜索引擎没有帮助的口语表达。

### 8.2 处理内容

- 使用 Clarification 后的 `resolved_query`。
- 提取核心主题、方法名、缩写、年份和比较对象。
- 为论文源生成英文检索表达，同时保留原始问题用于最终回答。
- 不允许改写增加用户没有要求的结论或研究对象。

### 8.3 特殊路由

若存在 `pdf_path`，改写后直接进入 Reason/Skill 路径，不执行 Query Plan 和在线 Retrieve。这是 PDF 本地阅读短路。

## 9. Query Plan：决定是否拆成多个子查询

### 9.1 简单任务

L1 通常只生成一个查询，`query_plan_enabled=false` 或使用单查询计划，避免过度拆分。

### 9.2 比较和研究任务

例如 GraphRAG 与 LightRAG 比较可拆为：

```text
T1：检索 GraphRAG 核心设计与证据
T2：检索 LightRAG 核心设计与证据
T3：基于 T1、T2 比较索引、查询、成本和适用场景
```

每个任务记录 ID、类型、查询、数据源建议和依赖关系。

### 9.3 Plan Validator

计划必须满足：

- 任务数量不超过上限；
- Task ID 唯一；
- 依赖引用存在；
- 依赖图无环；
- 检索任务不能依赖未来任务；
- 最终综合任务必须有足够上游证据。

不合法计划会回退到安全的确定性计划，而不是执行模型生成的任意 DAG。

## 10. Research Scheduler：把计划转为可执行波次

Scheduler 不负责生成计划，而是根据依赖关系安排顺序。

```text
Wave 1：所有无依赖任务，可受限并行
Wave 2：依赖 Wave 1 的任务
Wave 3：更深层综合任务（如存在）
```

- 同一波次最多使用配置允许的并发数。
- 并发只用于彼此独立的检索，不并行执行存在依赖的综合任务。
- 循环依赖、缺失任务或超过限制时标记 `invalid/blocked`。
- 当前项目的“并行”是有界工程优化，不是无限生成子 Agent。

## 11. Retrieval Router：决定去哪里找证据

### 11.1 Online

适合“最新论文”“找外部工作”“按作者或年份检索”等任务。

- 数据源：arXiv、OpenAlex、Crossref、Semantic Scholar。
- 可以单源检索，也可以多源并行后合并。
- Crossref/Semantic Scholar 更多承担元数据补全和交叉验证，具体是否调用受配置、路由和数据可用性影响。

### 11.2 Personal Library

适合“根据我收藏的论文”“从我的知识库中总结”。

- 必须已登录并有 `user_id`。
- 当前个人库生产路径以 Owner-scoped BM25 为核心，确保用户隔离。
- 项目级 Local RAG 另有 Dense + BM25 + RRF；不要把两者描述成当前完全相同的索引实现。
- 用户未登录或库不可用时明确停止，不能用公开论文冒充个人资料。

### 11.3 Hybrid

适合“结合我收藏的论文和最新在线论文”。

- Personal 与 Online 作为两个独立分支并行执行。
- 两边分别保留来源状态，即使一边失败也能说明缺失原因。
- 结果统一去重后进入 Evidence Store。
- Private Evidence 和 Public Evidence 保留不同来源标签。

### 11.4 PDF Reading

适合用户指定 PDF 的全文、页面或图表问题。

- 普通问题：PDF 文本路径。
- 图表问题：关键页 PNG + 页面文本路径。
- PDF 阅读不需要再去 arXiv 搜索，除非未来明确设计“PDF + Online”复合任务。

## 12. Tool / MCP 执行链

在线或外部能力不是由 LLM 直接任意调用，而是经过四层治理。

### 12.1 Tool Router

- 输入：能力名称和目标来源，例如 `paper.search + arxiv`。
- 作用：选择逻辑工具名，不直接执行网络请求。
- 失败：没有匹配路由时返回受控错误，不能猜测不存在的工具。

### 12.2 Tool Registry

- 保存工具名称、版本、输入模型、输出约定和执行函数。
- 保证不同节点和 Agent 使用同一个注册定义。
- MCP 工具与原生工具都可以注册，调用方不需要了解内部传输方式。

### 12.3 Tool Policy

- 检查工具是否允许、请求范围是否合规、是否需要显式配置。
- 例如 GitHub 代码增强只有用户明确要求且配置启用时才执行。
- Policy 是确定性代码，最终权限不交给 LLM。

### 12.4 Tool Executor

- 使用 Pydantic 校验参数。
- 执行超时、有限重试、异常捕获和统一结果封装。
- 输出包含 `success`、数据、错误类型、耗时、工具版本和审计信息。

### 12.5 MCP 的位置

MCP 是工具的标准化暴露协议，不是检索算法，也不是多 Agent 的必需条件。项目使用 MCP 兼容边界接入 GitHub、Zotero 等能力，使同一工具可以被不同 Agent 或外部客户端复用。

## 13. Retrieve：真正执行检索

### 13.1 单查询

优先级为：`retry_query → sub_query → rewritten_query → original query`。选择检索范围后执行相应 Retriever。

### 13.2 多查询

- 多个独立子查询可受限并行。
- 每个查询保留自己的来源状态和工具执行记录。
- 所有文档最终合并、去重并限制 Top-K。

### 13.3 Local RAG

项目级本地 RAG 流程：

```text
PDF Chunk
→ Dense Retriever 计算语义相似度
→ 检查 Top-1 分数和分数间隔
├─ 高置信度 → 使用 Dense 排名
└─ 低置信度 → BM25 + Dense，经 RRF 融合
```

这种门控避免所有查询都承担 Hybrid 成本，同时让术语检索和语义检索互补。

### 13.4 多源结果处理

- 使用论文 ID、DOI、arXiv ID、标题规范化结果去重。
- 合并同一论文来自不同平台的元数据。
- 可通过权威来源修复年份、作者或 DOI 冲突。
- 重排主要使用查询相关性、元数据完整度、来源和业务规则；当前在线重排不等同于所有结果都做向量化。

## 14. Repository Enrichment：可选代码实现证据

当用户明确询问 GitHub、实现代码或开源仓库，且配置允许时触发。

```text
GitHub Search MCP
→ 得到候选仓库
→ 只检查排名靠前的有限候选
→ GitHub Inspect MCP
→ 生成 repository 类型 Evidence
```

代码仓库证据只能支持“是否有实现、依赖和目录结构”等工程声明，不能替代论文实验结果。

## 15. Evidence Store：把检索结果变成可验证证据

`documents` 是原始检索结果；Evidence Store 是面向研究计划和验证链的标准化证据层。

### 15.1 类型化证据

常见类型包括论文、PDF 页面、个人库 Chunk、代码仓库和视觉证据。每条证据获得稳定 Evidence ID。

### 15.2 来源定位

保存标题、来源、URL/DOI、页码、文档 ID、用户归属和检索任务 ID，使回答中的声明能回到具体来源。

### 15.3 去重和规范化

相同论文的多个来源合并；冲突元数据保留告警；无定位信息的证据降低可信度或隔离。

### 15.4 Task ↔ Evidence 映射

证据不只是“堆在列表中”，还要记录它支持哪个研究子任务。这是 Coverage 检查的基础。

## 16. Research Coverage：回答前先判断证据够不够

Coverage 关注“计划要求的证据是否齐全”，Evaluate 更关注“当前检索结果总体质量是否够高”。

检查内容：

- 每个必需检索任务是否至少有证据；
- 比较任务的双方实体是否都覆盖；
- 是否存在只有代码而没有论文的错误替代；
- Evidence ID 和任务映射是否有效；
- 覆盖比例是否达到门槛。

不足时生成缺口列表，供 Replan 做定向补检，而不是简单重复同一搜索。

## 17. Evaluate：检索质量门控

### 17.1 规则评分

当前门槛为 `0.7`。规则综合考虑文档数量、查询词命中、Coverage、比较双方是否齐全和工具失败状态。

### 17.2 可选 LLM 评分

只有配置开启时才使用 LLM 判断相关性；失败时回退到规则评分。生产逻辑不能因为评估模型不可用而完全中断。

### 17.3 输出状态

- `accepted`：首次检索达到门槛。
- `recovered`：重试后达到门槛。
- `insufficient`：证据不足。
- `retry_budget_exhausted`：已经使用一次重试仍不达标。

## 18. Retrieval Replan：有限检索恢复

只有 `retrieval_score < 0.7` 且 `retry_count < 1` 时进入。

- 无结果：放宽或重组查询。
- 结果相关性低：保留核心实体，删除噪声限制。
- 比较缺一方：只补缺失对象。
- 工具失败：根据可恢复错误选择同查询重试或替代来源。

Replan 会记录原查询、新查询、失败类型和触发原因。最多一次，避免无限 Agent Loop。

## 19. Reason 与 Skill Router：选择怎样回答

### 19.1 Reason

Reason 根据问题、PDF 状态和研究分析确定 `task_type`。规则高置信度时直接决定；只有模糊情况才可调用 LLM。

### 19.2 Skill Router

Skill 不是外部工具，而是“如何组织输入和输出”的领域能力模板。

- QA：针对明确问题给出直接回答。
- Summary：概括单篇或多篇论文。
- Compare：按统一维度比较双方，禁止证据单边。
- Citation：强调引用格式和来源定位。
- Literature Review：多论文综合、研究脉络和空白。
- Paper Critique / Limitation：方法、实验和局限分析。
- Trend Analysis：按时间和主题总结趋势。
- Figure / Table / Chart / Formula：选择对应视觉提示词和 Pydantic 输出契约。

Skill 选择结果写入状态，Generate 只加载所选 Skill，不把所有提示模板同时发送给模型。

## 20. Generate / Research Writer：基于证据生成答案

### 20.1 输入

- 原始与改写后的问题；
- 所选 Skill；
- Top-K Evidence 和 Evidence ID；
- Research Brief/Plan；
- 可选长期记忆上下文；
- PDF 文本和视觉结构化结果。

### 20.2 生成约束

- 重要结论必须绑定 Evidence ID。
- 证据没有覆盖的内容明确说明不足。
- 代码证据和论文证据不能混用。
- PDF 模糊刻度、颜色、公式下标不能凭常识补齐。
- Coverage 未通过时输出受限结论或证据不足说明。

### 20.3 PDF 视觉双模型路径

```text
qwen3.5-ocr：理解选定页面
→ Figure/Table/Chart/Formula 结构化结果
→ qwen3.7-max：结合页面文本和视觉结果综合回答
```

### 20.4 Memory Metadata

L2/L3 在同一次生成调用中额外返回内部元数据：`worth_storing`、`memory_type`、`value_score`、`stability`、`time_sensitive`。这不会单独增加一次“是否值得记忆”的 LLM 调用。

## 21. Verification Pipeline：生成后逐层验证

### 21.1 Citation Validator

- 检查答案中 Evidence ID 的格式。
- 检查引用 ID 是否真实存在于 Evidence Store。
- 检查需要引用的研究结论是否缺少引用。
- 它验证“引用是否合法”，不完全判断“引用内容是否真的支持声明”。

### 21.2 Citation Repair

- 对缺失、位置错误或无效引用执行确定性修复。
- 只能使用已有 Evidence ID，不能创造新证据。
- 记录修复行数和状态：`not_triggered/repaired/partially_repaired`。

### 21.3 Claim-Evidence Validator

逐条检查研究声明与证据的语义关系：

- `supported`：证据直接支持。
- `partial`：只能支持声明的一部分。
- `contradicted`：证据与声明冲突。
- `insufficient`：证据不足以判断。

它输出声明支持率，是幻觉抑制的核心，而不仅是 Prompt 中一句“请勿编造”。

### 21.4 PDF Grounding Validator

仅 PDF 任务触发，检查：

- 回答是否只引用实际解析的页码；
- 视觉模型输出是否满足结构化 Contract；
- 关键描述是否能在页面文本或视觉证据中找到依据；
- 视觉链路失败时是否正确标记降级。

### 21.5 Answer Verifier

综合检查最终答案：相关性、完整性、证据状态、格式和失败说明，并给出通过状态和分数。它是进入 Reflection 和 Memory Write Gate 前的总闸门。

## 22. Answer Reflection：有限答案修复

仅在以下条件同时满足时触发：

- Answer Verification 未通过；
- 问题属于允许修复的失败类型；
- 已经有足够证据可用于修复；
- `answer_reflection_count < 1`。

Reflection 使用验证反馈重写一次答案，然后重新进入 PDF Grounding 和 Answer Verification。若新分数没有提高，系统恢复修复前答案并记录 `reflection_no_improvement`，避免“越改越差”。

## 23. Memory Write Gate：决定哪些结论值得长期保存

### 23.1 前置硬条件

- 任务通常是 L2/L3；
- Answer、Citation、Claim 和适用的 PDF Grounding 验证通过；
- 模型给出的 Metadata 格式有效。

### 23.2 Policy 判断

- `worth_storing` 是否为真；
- `value_score` 是否达到配置阈值；
- `stability` 是否适合长期保存；
- `time_sensitive` 是否应作为有期限 Snapshot；
- 是否与已有记忆重复、可合并、需要更新或存在冲突。

### 23.3 最终动作

- Write：新增长期结论。
- Merge：与重复记忆合并。
- Update：新证据形成新版本。
- Skip：价值低、验证失败或内容不稳定。
- Conflict Reject/Audit：冲突内容不直接覆盖，进入审计记录。

LLM 只提供语义建议，最终写入权由代码 Policy 控制。

## 24. Multi-Agent Finalize：有界角色交接

当前项目不是多个自治进程互相对话，而是将 L3 已有结果组织为三个可审计角色：

- Planner：Research Brief、任务数、依赖和执行波次。
- Executor：工具执行、Evidence Store 和 Coverage 状态。
- Reviewer：Citation、Claim、Grounding 和 Answer Verification。

该节点汇总角色输入输出和交接状态，额外 LLM 调用为 0。它展示 Multi-Agent 协作边界，而不制造昂贵的角色聊天。

## 25. Metrics / Trace / Stop Reason：记录系统为什么这样结束

### 25.1 Metrics

记录：

- 总耗时和每个节点耗时；
- LLM 调用次数、失败次数、输入/输出 Token；
- 检索数量、去重数量、来源状态和缓存命中；
- Coverage、Citation、Claim、Grounding、Answer 分数；
- Replan、Reflection 和 Memory Gate 状态。

### 25.2 Trace

Trace 展示实际经过的节点和工具，不是预先画好的固定流程。问候、PDF、L1 和 L3 的 Trace 会不同。

### 25.3 Stop Reason

明确系统为什么停止，例如：

- `quality_threshold_met`；
- `retry_budget_exhausted`；
- `reflection_no_improvement`；
- `clarification_required`；
- `requested_scope_unavailable`。

Stop Reason 让“没回答完整”成为可解释的策略结果，而不是静默失败。

## 26. 最终输出层

### 26.1 中文研究回答

首先显示可读结论，不直接展示 Markdown 源代码。标题、段落、列表和引用由前端按普通 AI 回答渲染。

### 26.2 论文证据与引用

用户可以查看标题、来源、相关度、摘要、Evidence ID、URL/DOI 和 PDF 页码，验证回答依据。

### 26.3 LangGraph 执行轨迹

展示本次请求经过的节点、状态和耗时，帮助开发者定位问题，也用于面试解释 Graph Engineering。

### 26.4 Token、延迟与工具记录

用于分析成本和性能，判断某项能力是否值得开启，而不是只看最终回答是否“像是正确的”。

### 26.5 Word / PDF 研究报告

- 复用已经生成并验证的答案与证据。
- 导出过程不再次调用 LLM。
- 报告包含问题、结论、证据索引、检索范围、质量状态和 Trace ID。

## 27. 四种典型请求实际经过哪些模块

### 27.1 输入 `hi`

```text
Web/API/CLI
→ PaperAgentService
→ State
→ Intent Router：smalltalk
→ 本地回答
→ 结束
```

不调用 LLM、不检索、不加载长期记忆。

### 27.2 “检索有关 RAG 的论文”

```text
Service → Intent → Clarification
→ Research Analyzer：L1
→ Memory：不需要
→ Rewrite → 单查询 Plan
→ Online Route
→ Tool Router/Registry/Policy/Executor
→ arXiv/OpenAlex
→ Evidence → Coverage/Evaluate
→ Skill：QA 或 Paper Ranking
→ Generate → Verification
→ Metrics → Answer
```

### 27.3 “比较 GraphRAG 和 LightRAG 的核心设计”

```text
Service → Intent → Clarification
→ Research Analyzer：L2
→ Rewrite
→ Plan：GraphRAG / LightRAG / Compare
→ Scheduler：前两项并行，比较项后执行
→ Multi-source Retrieve
→ Evidence Store
→ Coverage：双方是否都有证据
→ 不足则定向 Replan 一次
→ Compare Skill
→ Writer
→ Citation + Claim + Answer Verification
→ Memory Write Gate
→ Metrics → Answer/Report
```

### 27.4 “解释这篇 PDF 第 4 页的架构图”

```text
Service：加载 PDF 第 4 页文本和 PNG
→ Intent → Clarification → Analyzer
→ Rewrite 后 PDF 短路
→ Reason：pdf_reading
→ Skill：figure_understanding
→ qwen3.5-ocr 页面视觉解析
→ qwen3.7-max 综合
→ Citation → Claim → PDF Grounding → Answer Verify
→ Metrics → Answer/Report
```

## 28. 按开发阶段理解这些模块

### 阶段 1：最小 LangGraph 闭环

Intent Router → Query Rewrite → Retrieve → Evaluate → Reason → Generate → Metrics。

作用：先证明状态图、条件路由和端到端问答能运行。

### 阶段 2：检索和工具工程

Query Plan、Tool Router、Registry、Policy、Executor、多源检索、去重、重排、缓存和 Replan。

作用：让“找论文”从单个 Adapter 升级为可治理、可恢复的工具系统。

### 阶段 3：Research Agent

Research Analyzer、Research Brief、Plan Validator、Scheduler、Evidence Store、Coverage、Research Writer。

作用：从简单论文搜索升级为可以拆解和综合开放研究问题的 Agent。

### 阶段 4：证据和幻觉抑制

Citation Validator、Citation Repair、Claim-Evidence、PDF Grounding、Answer Verifier、Answer Reflection。

作用：把“模型说得像答案”升级为“每个关键结论都有可检查依据”。

### 阶段 5：RAG、个人知识和记忆

Local RAG、Personal Library、Hybrid、Conversation Memory、Checkpoint、Memory Retrieval、Memory Write Gate。

作用：结合私人材料、公开知识和历史研究结论，同时保持用户隔离和写入治理。

### 阶段 6：多模态和产品交付

PDF 自动选页、视觉 Skills、Web Console、认证、Word/PDF 导出、Docker、CI、测试报告。

作用：把后端能力变成可实际演示、可部署、可评估的完整简历项目。

## 29. 当前实现与架构图中抽象表达的区别

- 图中的 Skill Registry 是统一概念；当前实际通过 Skill Router 和 Python Skill 注册实现，不依赖 LLM 自由发现技能。
- 图中的 Multi-Agent 是 Planner/Executor/Reviewer 有界角色汇总，不是三个常驻自治 Agent。
- 图中的 Personal Library 当前以 Owner-scoped BM25 为主；项目级 Local RAG 才有 Dense/BM25/RRF 门控。
- 图中的 Redis、独立向量数据库、团队 RBAC、完整 GraphRAG/LightRAG 属于扩展方向，不应描述为当前生产能力。
- Crossref、Semantic Scholar、GitHub、Zotero 是否在某次请求中调用由路由、配置和用户意图决定，不是每次固定全部调用。
- “ReAct 循环”在本项目中是受预算约束的 Replan/Reflection，不是无限 Thought-Action-Observation 循环。

## 30. 一句话总结架构设计

PaperAgent 的核心不是模块数量，而是把每次研究请求变成一条可解释的状态链：先控制是否值得执行，再澄清和规划；随后用受治理工具收集证据，以 Coverage 和质量评分决定是否恢复；最后用多级验证限制生成结果，并把成本、停止原因和证据全部暴露给用户。

## 31. 受控策略进化旁路

策略进化不在用户请求主链路中同步运行，而是消费 Eval/Trace 的离线 Harness：

```text
Trace / Eval Report
→ Failure Dataset
→ Failure Attribution
→ Allowlisted Strategy Candidates
→ Baseline / Candidate Frozen Eval
→ Promotion Gate
→ Version Registry
→ Human Approval
```

它可以建议 Prompt、Few-shot、Policy、Retrieval 和 Routing 变化，但不能自动修改源码、权限、认证、部署或 active version。这样“系统会学习失败”与“系统可以不受控制地自我修改”被明确区分。
