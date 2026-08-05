# PaperAgent 开发路线图

本文档是项目后续能力升级计划的唯一正式来源。开发应按照下方依赖顺序推进，后续阶段不得绕过前置阶段建立的接口、评测门槛或安全控制。

## 当前能力基线

项目当前已经具备：

- 对问候、感谢和身份问题进行本地意图路由；
- 基于规则的查询复杂度分类与动态查询规划；
- 带本地 JSON 缓存和静态兜底文档的 arXiv 检索；
- 统一 ToolSpec、ToolResult、Tool Registry、Tool Router、Tool Executor、只读 ToolPolicy 和 arXiv Native Adapter；
- 多查询结果合并与去重；
- 带有限重试的检索质量评估；
- QA、总结、比较、引用、研究方向推荐和 PDF 阅读技能；
- 按节点统计 LLM Token、延迟、失败和成本所需的用量数据；
- 确定性离线能力基准测试和单元测试 Excel 报告。

当前主要限制：

- 外部论文搜索仅支持 arXiv；
- 尚未建立完整的本地 RAG 链路，当前优化主要属于 LangGraph 查询规划、多查询检索、结果合并和有限重试；
- 当前只注册了 arXiv 一个原生工具，尚未接入多数据源和 MCP 工具；
- Tool Router 仍是确定性来源映射，尚未加入数据源可用性、成本、限流和质量驱动选择；
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
| Agentic RAG / Query Planning | 第一版完成 | 已有复杂度分类、多查询规划、检索合并与重试 | 增加重排、多源检索和失败类型驱动的重新规划 |
| Structured Memory | 未完成 | 已有基础对话历史 | 增加摘要、重要事实、活跃论文、研究偏好和策略记忆 |
| Tool Governance | 第一版完成 | 已有统一协议、Registry、Router、Executor、只读 Policy、arXiv Adapter、指标与离线 Benchmark | 增加多源路由、限流、细粒度授权和 MCP Adapter |
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

阶段 1 第一版已完成，下一项只实现阶段 2 的“第二个原生论文数据源接入”，暂不同时引入 RAG、MCP、Redis 或 Agent Loop：

```text
选择一个只读候选数据源（OpenAlex 或 Semantic Scholar）
→ 通过统一 Tool 协议实现 Native Adapter
→ 定义统一 PaperDocument 字段与跨源错误映射
→ 增加确定性 Tool Router 路由规则
→ 保持 arXiv 单源模式作为关闭开关和基线
→ 增加正常、空结果、限流、超时和字段缺失测试
→ 使用固定论文查询集比较覆盖率、去重、延迟和工具调用成本
→ 只有数据证明有收益后才晋升默认多源路线
```

完成第二个原生数据源后，再判断继续扩展多源检索还是开始本地 RAG 标注集；MCP、Agent Loop、LLM Wiki 和 Agent 自进化继续建立在统一 Tool 与 Harness 接口之上。
