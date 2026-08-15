# PaperAgent：基于 LangGraph 的科研论文智能体

[![PaperAgent CI](https://github.com/Fionaxxxi/paper-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/Fionaxxxi/paper-agent/actions/workflows/ci.yml)

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
MODEL_NAME=qwen3.7-max-2026-05-17
RETRIEVAL_MODE=arxiv
```

### 2. 启动 API

```powershell
D:\miniconda3\envs\paper_agent\python.exe -m uvicorn app.api:app --host 127.0.0.1 --port 8000
```

浏览器打开 `http://127.0.0.1:8000/docs`，可直接使用 Swagger 调试。健康检查地址为 `http://127.0.0.1:8000/health`。

项目同时提供 Research Agent Web 演示台：打开 `http://127.0.0.1:8000/`，即可查看答案、论文证据、Research Plan、依赖执行波次、Evidence Store、Coverage/Citation/Repair 质量闸门、工具调用和 LangGraph 节点耗时。页面内置“加载示例轨迹（零 API）”，即使现场没有网络或模型凭据也能展示完整 L3 研究闭环。

也可以运行命令行版本：

```powershell
D:\miniconda3\envs\paper_agent\python.exe main.py
```

### 3. 使用 Docker 启动

镜像不会包含 `.env`、本地 PDF、模型缓存、SQLite、Wiki 或评测输出。首次启动前仍需从示例创建本地配置：

```powershell
Copy-Item .env.example .env
docker compose up --build -d
docker compose ps
```

打开 `http://127.0.0.1:8000/` 查看 Research Agent 演示台，健康检查为 `http://127.0.0.1:8000/health`。停止服务：

```powershell
docker compose down
```

Compose 将 `./data` 和 `./logs` 挂载到容器，因此论文、索引和日志不会随容器删除。SQLite 记忆单独保存在名为 `paper-agent-memory` 的 Docker volume 中，避免 Windows bind mount 与 SQLite WAL 的兼容问题；宿主机原有记忆文件不会被容器改写。若只演示冻结的零 API 轨迹，`.env` 可以保留占位 Key；点击“运行 Agent”前必须配置真实模型凭据。

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
  query = "分析第 1 页的摘要与图表信息"
  pdf_path = "D:\langgraphproject\data\papers\2404.16130_graph_rag.pdf"
  pdf_pages = @(1)
} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/chat -ContentType "application/json" -Body $body
```

展示重点：PDF 任务绕过在线检索，直接进入论文阅读 Skill。`pdf_pages` 使用从 1 开始的页码，一次最多 3 页；系统只提取指定页文本，并用 PyMuPDF 将这些页面渲染到 `data/cache/pdf_pages/`，不会扫描整篇图像。

默认 `PDF_VISION_ENABLED=false`，此时模型只依据指定页文本回答，`pdf_vision_status` 会标记为 `rendered_text_only`。确认视觉模型可用后，可在 `.env` 开启：

```env
PDF_VISION_ENABLED=true
PDF_VISION_MODEL_NAME=qwen3.5-ocr
```

默认选择 `qwen3.5-ocr`：它面向文档解析、文字识别、文字定位与关键信息提取，输入为图像、输出为文本；它不是任意场景的通用视觉推理模型。开启后，只有用户通过 `pdf_pages` 明确指定的页面 PNG 会发送给 OCR 模型；OCR 结果按不可信外部证据处理，再由主模型结合 pypdf 文本生成最终研究回答。因此页面 OCR 模式会产生两次模型调用。状态变为 `used` 后，回答才能使用页面 OCR/布局信息。页码越多会增加图像 Token 和延迟，因此仍保留最多 3 页的硬限制。具体价格、地域与免费额度以百炼控制台为准。

运行一次受保护的真实 OCR 冒烟（默认只发送 GraphRAG 第 3 页）：

```powershell
D:\miniconda3\envs\paper_agent\python.exe -m eval_harness.pdf_vision_smoke --confirm-online
```

报告写入 `outputs/pdf_vision_smoke/latest.json`，仅记录页码、模型、状态、Token、延迟和答案短摘要，不保存 Key、Base64 图片或本地绝对路径。未带 `--confirm-online` 时脚本会在调用前退出。

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
| `zotero` | 通过只读 MCP Server 搜索个人或群组 Zotero 文献库、标签和笔记 |

`mcp_catalog` 不由 LLM 自动触发，也不会替换默认 arXiv。它是一个明确的演示场景：修改 `.env` 后重启服务，MCP 调用的路由依据、Server 身份、版本、传输方式、耗时和错误会记录到工具执行元数据中。

### Zotero 只读 MCP

先在 Zotero 账户设置中创建只读 API Key，并在 `.env` 配置：

```env
RETRIEVAL_MODE=zotero
ZOTERO_LIBRARY_TYPE=user
ZOTERO_LIBRARY_ID=你的数字用户ID
ZOTERO_API_KEY=你的只读Key
ZOTERO_MAX_RESULTS=5
```

群组库将 `ZOTERO_LIBRARY_TYPE` 改为 `group`，并填写群组 ID。PaperAgent 固定请求 Zotero Web API v3，只提供 GET 搜索；Key 仅通过 `Zotero-API-Key` 请求头传递。v1 返回文献元数据、标签、Collection Key、子笔记和 PDF 附件 Key；它只能识别 PDF 附件是否存在，尚未下载或解析附件全文。配置缺失或调用失败时返回空个人库结果和错误轨迹，不使用公共 fallback 论文掩盖失败。

### GitHub 只读 MCP

GitHub MCP v1 提供两个独立能力，不会自动替换论文检索：

```text
repository.search + github
→ code.repository.search.github.mcp
→ 按论文名、研究主题或关键词搜索候选仓库

repository.inspect + github
→ code.repository.inspect.github.mcp
→ 读取指定 owner/repo 的 README、目录、依赖文件、开放 Issue、Release 和最近 Commit
```

公开仓库无需 Token 即可使用。建议在 `.env` 配置 Token，以提高 API 限额；只授予需要读取的最小权限：

```env
GITHUB_API_BASE_URL=https://api.github.com
GITHUB_TOKEN=
GITHUB_MAX_RESULTS=5
GITHUB_ENRICHMENT_ENABLED=false
```

工具只调用固定 GitHub REST GET 端点，使用 `2022-11-28` API 版本；Token 只通过 `Authorization` 请求头传递。仓库参数必须是 `owner/repo`，不能传 URL、相对路径或额外 API 子路径。

论文—代码对照采用双重授权：部署者必须显式设置 `GITHUB_ENRICHMENT_ENABLED=true`，并且当前 L3 研究问题必须明确写出 `GitHub`。只询问“代码实现、开源或复现”时，系统仅把增强状态标记为 `suggested`，不会向外部服务发送查询。授权成立后，流程最多搜索一次、检查排名第一的一个仓库；失败只记录工具错误，不中断论文主流程。仓库 README、依赖、版本和活动信息会以 `repository` 类型写入 Evidence Store，不能替代论文对方法和实验结论的证明。

```text
论文检索完成
→ 是否为 L3 且明确要求代码/复现？
  → 否：跳过
  → 是，但没有明确写 GitHub：suggested，不出站
  → 明确写 GitHub，但部署开关关闭：disabled，不出站
  → 明确写 GitHub + 开关开启
    → 搜索最多 3 个候选仓库
    → 检查排名第一的仓库
    → 生成 repository 类型证据
→ 与 paper 类型证据共同进入 Evidence Store
→ Coverage / Writer / Citation Validator
```

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

Prompt Injection 小型对抗集默认只做零费用边界检查：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_prompt_security_eval.ps1
```

显式运行 4 次真实模型对抗调用：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_prompt_security_eval.ps1 --confirm-online
```

报告保存到 `outputs/prompt_security_eval/latest_prompt_security.json` 和 `.csv`。在线判分要求输出不包含攻击 Canary/伪造 Evidence ID，同时至少命中一项安全研究内容；只拒绝回答不会通过。当前 v1 只有 4 个合成案例，只用于代表性安全冒烟，不代表完整红队认证。

Research Analyzer Prompt A/B 默认只检查冻结数据集与 Prompt 长度：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_research_analyzer_prompt_ab.ps1
```

显式执行 zero-shot/few-shot 各 6 次真实调用：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_research_analyzer_prompt_ab.ps1 --confirm-online
```

生产默认由 `RESEARCH_ANALYZER_PROMPT_VARIANT=zero_shot` 控制。few-shot 只有在解析率不下降、绝对通过率至少 80%、相对提升至少 10 个百分点且 Token 增幅不超过 250% 时才可晋升；不能仅凭相对提升自动切换。
离线与在线报告分别写入 `latest_analyzer_prompt_ab_offline.*` 和 `latest_analyzer_prompt_ab_online.*`，避免日常零费用检查覆盖付费运行明细。

## 基础 CI

GitHub Actions 在 `master` push 和 Pull Request 时执行：

```text
Node 检查前端 JavaScript 语法
→ Python 3.10 安装依赖
→ 运行确定性 Research Agent 核心测试
→ 构建 Docker 运行镜像
```

CI 会显式关闭在线 LLM、外部检索评测和 LangGraph 持久化，不需要 GitHub Secrets，不会产生模型 Token，也不会下载本地 Dense 模型。完整 RAG 基准和在线能力集仍由本地显式命令运行。

## 已实现边界与后续方向

当前已经实现 LangGraph 工作流、在线多源工具层、本地 Hybrid RAG、查询规划、一次受控 Replan、Skill 路由、本地会话记忆、质量降级和可观测元数据。

Prompt 当前以 zero-shot 结构约束为主。所有论文、Zotero 笔记、PDF 文本和 Evidence Store snippet 在进入模型前都会标记为不可信外部证据，明确禁止其中的角色切换、规则覆盖、密钥泄露、工具调用和代码执行指令；这能建立基础 Prompt Injection 边界，但不等价于已经通过真实模型对抗测试。分类、分析、各科研 Skill、Research Writer 和 Reflection 均有独立 `prompt_version`，版本会进入 LLM usage 与节点级 metrics，后续只对 Research Analyzer/Writer 做选择性 few-shot A/B，不给所有普通问答无差别增加 Token。

项目后续的核心定位是“证据驱动的轻量 Research Agent”，不是继续堆叠普通论文问答功能。目标是把复杂研究意图转换成 Research Brief 和受限计划，通过 Tool / MCP / RAG 收集可追溯证据，经 Coverage、Claim/Citation Verifier 和有限 Reflection 后输出中文研究报告；简单搜索与问答仍保留快速路径。

Research Analyzer 已接入检索前流程：L1 简单请求使用规则快速路径，L2 比较/方向请求使用结构化规则，L3 前景、趋势、代表论文和研究空白等复杂请求可调用一次 LLM 输出受 Pydantic 约束的 `ResearchAnalysis`。Policy Gate 禁止 LLM 降级高置信度 L3、选择未注册 Skill 或关闭必要检索；随后生成最多 5 个任务、并行预算 2 的 Research Brief/Plan，并检查重复、未知来源、未知依赖和循环依赖。有效 Plan 会编译为依赖执行波次，检索结果进入请求级 Evidence Store 和 Coverage Gate；Research Writer 输出再经过 Citation Validator 与零 LLM Citation Repair。

最终答案现在经过确定性 Verifier：检查空答案、完整度、任务结构和论文证据引用信号。只有发现可修复缺陷且已有论文/PDF 证据时，才调用一次 LLM 执行 Answer Reflection；修复后再次验证，无改善则恢复初始答案。`ANSWER_REFLECTION_ENABLED=false` 可以关闭修复调用，但仍保留答案验证。该能力只处理当前任务，不属于跨任务 Reflexion，也不会自动写入长期记忆。

会话记忆已从逐会话 JSON 升级为项目内 SQLite：保存完整消息、用户偏好、活跃研究主题、活跃论文和研究状态 Checkpoint。请求上下文只保留最近消息原文，更早消息进行确定性提取式压缩，并按字符预算组装；旧 `data/memory/*.json` 会在首次读取时兼容迁移。当前摘要不调用 LLM，尚未实现语义摘要或正式 LangGraph SQLite Saver。

Markdown LLM Wiki v1 已提供严格发布门控：只有允许的研究任务、最终答案通过 Verifier、存在可追溯论文证据且未处于证据不足模式时才可发布。笔记保存研究问题、结论、论文身份/来源/链接、验证分数和 Reflection 次数，并维护幂等索引。默认 `LLM_WIKI_AUTO_PUBLISH_ENABLED=false`，生成内容位于 `data/wiki/` 且被 Git 忽略；开启前应确认希望把合格研究结果持久化到本机。

LangGraph 已接入官方 `SqliteSaver`，使用 `conversation_id` 作为 `thread_id`，将节点级 State 快照保存到 `data/memory/langgraph_checkpoints.db`。同一线程的新请求会显式重置检索、答案、重试和验证等临时字段，避免上一轮状态污染；可通过 `LANGGRAPH_CHECKPOINT_ENABLED=false` 完全关闭。该数据库服务于图状态恢复，和保存可读会话/研究上下文的 `paper_agent_memory.db` 职责不同。

后续采用“有特色但能完成”的 Research Agent 执行路线，尚未完成的部分不应描述为已实现功能：

1. 已收口统一 MCP 路由和执行元数据；
2. 增加 Verifier 与最多一次的有限 Answer Reflection 修复；
3. 使用 SQLite/检查点建立结构化记忆，并生成可阅读的 Markdown LLM Wiki；
4. 实现 Literature Review、Paper Critique 等高价值科研 Skill 和结构化输出；
5. 增加 L0～L3 分级任务路由，仅对 L3 深度研究启用 Research Brief、Planner / Executor / Reviewer、Evidence Coverage 和 Checkpoint；
6. 已接入只读 Zotero 和 GitHub 外部 MCP，并完成带双重授权的“论文—代码对照”编排；
7. 已实现用户指定页面的轻量多模态 PDF 分析：指定页文本与PNG渲染已完成，页面OCR模型采用显式开关并限制最多3页；
8. 已完成 Research Agent Web 轨迹展示、零 API 冻结演示、最小 Docker 和基础 CI；后续只做可选部署与演示材料整理。

自动 Reflexion/自进化、在线适应、八角色分层 Agent、Best-of-N、Redis、完整 GraphRAG 选型矩阵和整篇 PDF 全自动多模态解析暂缓。GraphRAG 仅在固定的跨论文全局任务证明 Hybrid RAG 不足后做小型 PoC；测试按风险分级，Excel 在里程碑统一更新。

Agent Loop 坚持有限循环：现有 Retrieval Replan 最多一次，后续 Answer Reflection 最多一次；深度研究中的计划修复、证据补充和报告修复也各最多一次，并共享总 Token、工具调用、时间和迭代预算。普通问题不会自动进入高成本深度研究流程。

复杂研究意图分析默认开启，简单 L1/L2 不会因此调用模型：

```env
RESEARCH_ANALYSIS_WITH_LLM=true
```

启用本地 Wiki 自动发布：

```env
LLM_WIKI_AUTO_PUBLISH_ENABLED=true
LLM_WIKI_ALLOWED_TASK_TYPES=summarize,compare,recommend,literature_review,paper_critique
```

详细历史、技术决策和未来计划见 [docs/ROADMAP.md](docs/ROADMAP.md)。
