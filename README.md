# PaperAgent：基于 LangGraph 的科研论文智能体

PaperAgent 是一个面向科研论文场景的 Agent 项目。它不只是调用一次大模型，而是使用 LangGraph 编排意图识别、查询规划、多源检索、质量判断、受控重试、Skill 选择、答案生成和运行指标记录。

项目同时支持在线论文发现和本地论文全文 RAG，适合作为 Agent Engineering、Graph Engineering、RAG 和工具系统设计的综合实践项目。

## 项目特色

- **LangGraph 状态工作流**：每个阶段都是独立节点，支持条件路由、状态共享、失败恢复和可观测耗时。
- **低成本意图短路**：`hi`、感谢等简单输入直接本地回答，不进入检索和 LLM 流程。
- **查询规划与受控重试**：复杂问题可拆分为多个子查询；低质量结果最多执行一次有依据的 Replan，避免无限 Agent Loop。
- **统一工具层**：在线检索经过 Tool Router、Registry、Policy 和 Executor，统一处理参数、超时、重试与错误结构。
- **多论文源检索**：支持 arXiv、OpenAlex，以及可选的多源合并、去重、元数据校验和重排。
- **本地全文 RAG**：支持 PDF 解析、Chunk、BM25、Dense Retrieval、向量缓存和置信度门控 Hybrid。
- **可审计检索路由**：本地 RAG 会记录 Dense Top-1、分数间隔，以及最终选择 Dense 或 Hybrid 的原因。
- **多 Skill 回答**：根据任务选择问答、总结、比较、引用、研究方向或 PDF 阅读 Skill。
- **记忆与可观测性**：按 `conversation_id` 将最近会话保存在本地文件，并返回节点耗时、工具记录与 Token 用量。

## 当前架构

```text
用户 / FastAPI / 命令行
→ PaperAgentService：会话、PDF、Trace 初始化
→ LangGraph
   → Intent Router
      → 简单问候：本地回答并结束
      → 科研问题：继续工作流
   → Query Rewrite
   → Query Plan：简单查询或复杂任务拆分
   → Retrieve
      → 在线模式：Tool Router → Registry → Policy → Executor
         → arXiv / OpenAlex / Crossref / Semantic Scholar
      → 本地模式：PDF Chunk → MPNet Dense
         → 高置信度：Dense
         → 低置信度：复用 Dense 排名 + BM25 + RRF
   → Evaluate：检索质量判断
      → 通过：继续生成
      → 可恢复失败：最多一次 Retrieval Replan
      → 证据仍不足：安全降级回答
   → Reason：识别问答、总结、比较等任务
   → Skill Router
   → Generate
   → Metrics
→ 返回答案、论文、检索路由、工具记录、Token 与节点耗时
```

## 技术栈

| 类别 | 技术 | 作用 |
|---|---|---|
| Agent 编排 | LangGraph | 状态图、条件路由、重试和流程可观测性 |
| LLM 接入 | LangChain OpenAI | 兼容百炼等 OpenAI 协议接口 |
| API | FastAPI、Pydantic、Uvicorn | 接口定义、数据校验和服务运行 |
| 在线检索 | arXiv、OpenAlex、Crossref、Semantic Scholar | 论文发现与元数据补全 |
| 本地 RAG | PyPDF、FastEmbed、ONNX Runtime | PDF 解析与本地 Dense Retrieval |
| 混合检索 | BM25、MPNet、RRF | 词法和语义检索互补 |
| 缓存与记忆 | JSON、NumPy | 会话文件、在线结果和向量索引缓存 |
| 测试 | Pytest | 关键节点、工具契约和检索路径回归测试 |

## 快速开始

### 1. 进入项目并使用指定环境

```powershell
Set-Location D:\langgraphproject
D:\miniconda3\envs\paper_agent\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

在 `.env` 中至少配置：

```env
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_API_KEY=你的百炼_API_Key
MODEL_NAME=qwen-max
RETRIEVAL_MODE=arxiv
```

### 2. 启动 API

```powershell
D:\miniconda3\envs\paper_agent\python.exe -m uvicorn app.api:app --host 127.0.0.1 --port 8000
```

浏览器打开 `http://127.0.0.1:8000/docs`，可直接使用 Swagger 调试。健康检查地址为 `http://127.0.0.1:8000/health`。

项目同时提供 Web 演示台：打开 `http://127.0.0.1:8000/`，即可查看答案、论文证据、本地 Dense/Hybrid 路由、工具调用和 LangGraph 节点耗时。

也可以运行命令行版本：

```powershell
D:\miniconda3\envs\paper_agent\python.exe main.py
```

## 四个代表性演示

### 1. 在线论文检索

`.env`：

```env
RETRIEVAL_MODE=arxiv
```

PowerShell 请求：

```powershell
$body = @{ query = "检索并总结近期关于 RAG 查询规划的代表性论文" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/chat -ContentType "application/json" -Body $body
```

展示重点：查询规划、arXiv 工具调用、论文结果和生成答案。

### 2. 本地全文 RAG

`.env`：

```env
RETRIEVAL_MODE=local_rag
LOCAL_RAG_MAX_RESULTS=5
```

```powershell
$body = @{ query = "ReAct 如何结合推理与行动？" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/chat -ContentType "application/json" -Body $body
```

展示重点：真实 PDF Chunk、页码、Dense/Hybrid 路由和本地向量缓存。示例语料 PDF 需要按 `data/papers/corpus_sources.json` 放入 `data/papers/`；模型与索引保存在 `data/cache/`，这些大文件不会提交到 Git。

### 3. 指定 PDF 阅读

```powershell
$body = @{
  query = "总结这篇论文的研究问题、方法和局限"
  pdf_path = "D:\langgraphproject\data\papers\2005.11401_rag.pdf"
} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/chat -ContentType "application/json" -Body $body
```

展示重点：PDF 任务绕过在线检索，直接进入论文阅读 Skill。

### 4. 多轮会话

```powershell
$first = @{ query = "什么是 Self-RAG？"; conversation_id = "resume-demo" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/chat -ContentType "application/json" -Body $first

$second = @{ query = "它和普通 RAG 的主要区别是什么？"; conversation_id = "resume-demo" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/chat -ContentType "application/json" -Body $second
```

展示重点：相同 `conversation_id` 复用最近会话上下文，记录保存在 `data/memory/`。

## 检索模式

| `RETRIEVAL_MODE` | 行为 |
|---|---|
| `arxiv` | 默认模式，使用 arXiv 在线检索 |
| `openalex` | 使用 OpenAlex 检索 |
| `multi_source` | 按配置组合多个在线来源 |
| `local_rag` | 检索本地 PDF 全文知识库 |
| `mcp_catalog` | 通过显式 Tool Router 调用只读 stdio MCP Server，查询项目论文目录；主要用于演示 MCP 主链路 |

`mcp_catalog` 不由 LLM 自动触发，也不会替换默认 arXiv。它是一个明确的演示场景：修改 `.env` 后重启服务，MCP 调用的路由依据、Server 身份、版本、传输方式、耗时和错误会记录到工具执行元数据中。

## 测试

简历展示阶段采用轻量验收：新增能力主要运行代表性冒烟测试和关键回归测试，不再默认进行研究级大规模重复评测。

运行关键测试：

```powershell
D:\miniconda3\envs\paper_agent\python.exe -m pytest tests\test_graph_integration.py tests\test_local_rag_integration.py -q
```

需要完整回归时：

```powershell
D:\miniconda3\envs\paper_agent\python.exe scripts\run_tests_with_report.py
```

## 已实现边界与后续方向

当前已经实现 LangGraph 工作流、在线多源工具层、本地 Hybrid RAG、查询规划、一次受控 Replan、Skill 路由、本地会话记忆、质量降级和可观测元数据。

最终答案现在经过确定性 Verifier：检查空答案、完整度、任务结构和论文证据引用信号。只有发现可修复缺陷且已有论文/PDF 证据时，才调用一次 LLM 执行 Answer Reflection；修复后再次验证，无改善则恢复初始答案。`ANSWER_REFLECTION_ENABLED=false` 可以关闭修复调用，但仍保留答案验证。该能力只处理当前任务，不属于跨任务 Reflexion，也不会自动写入长期记忆。

后续采用“有特色但能完成”的执行路线，尚未完成的部分不应描述为已实现功能：

1. 已收口统一 MCP 路由和执行元数据；
2. 增加 Verifier 与最多一次的有限 Answer Reflection 修复；
3. 使用 SQLite/检查点建立结构化记忆，并生成可阅读的 Markdown LLM Wiki；
4. 实现 Literature Review、Paper Critique 等高价值科研 Skill 和结构化输出；
5. 增加 L0～L3 分级任务路由，仅对 L3 深度研究启用 Research Brief、Planner / Executor / Reviewer、Evidence Coverage 和 Checkpoint；
6. 依次接入只读 Zotero 和只读 GitHub 外部 MCP；
7. 实现用户指定页面的多模态 PDF 分析；
8. 完成 Web 轨迹展示、Docker、基础 CI 和端到端演示。

自动 Reflexion/自进化、在线适应、八角色分层 Agent、Best-of-N、Redis、完整 GraphRAG 选型矩阵和整篇 PDF 全自动多模态解析暂缓。GraphRAG 仅在固定的跨论文全局任务证明 Hybrid RAG 不足后做小型 PoC；测试按风险分级，Excel 在里程碑统一更新。

Agent Loop 坚持有限循环：现有 Retrieval Replan 最多一次，后续 Answer Reflection 最多一次；深度研究中的计划修复、证据补充和报告修复也各最多一次，并共享总 Token、工具调用、时间和迭代预算。普通问题不会自动进入高成本深度研究流程。

详细历史、技术决策和未来计划见 [docs/ROADMAP.md](docs/ROADMAP.md)。
