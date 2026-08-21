# PaperAgent 最终项目交付与演示手册

更新日期：2026-08-21  
目标读者：项目作者、简历面试官、代码评审者  
当前定位：证据驱动、成本受控、可验证的科研 Research Agent

## 1. 项目一句话介绍

PaperAgent 是一个基于 LangGraph 的研究型论文 Agent：它把用户问题转化为受限研究计划，通过在线论文源、个人论文库、Local RAG、MCP 和 PDF 视觉理解收集证据，再经过 Coverage、Citation、Claim、Grounding 和 Answer Verification 输出可追溯的中文研究结论，并支持导出 Word/PDF 报告。

它的重点不是“接一个大模型做论文问答”，而是展示一套完整的 Agent Engineering 闭环：

```text
理解任务
→ 制定计划
→ 选择数据源和工具
→ 收集与合并证据
→ 判断证据是否足够
→ 生成研究结论
→ 验证引用与声明
→ 必要时有限恢复
→ 记录成本、状态与可下载报告
```

## 2. 当前完成度

当前简历项目版本约完成 99%。主功能已经形成闭环，界面截图、发布核验清单和面试讲解稿也已补齐；剩余工作仅是远端 CI 绿灯确认和全新机器冷启动验收，不再需要继续堆叠研究型模块。

| 模块 | 状态 | 说明 |
|---|---|---|
| LangGraph 主工作流 | 已完成 | 条件路由、状态共享、Checkpoint、失败恢复与指标 |
| 多源论文检索 | 已完成 | arXiv、OpenAlex、Crossref、Semantic Scholar |
| Tool/MCP 治理 | 已完成 | Router、Registry、Policy、Executor、统一错误与审计 |
| 本地全文 RAG | 已完成 | PDF Chunk、BM25、Dense、RRF、置信度门控 Hybrid |
| Research Agent | 已完成 | L0-L3、Research Brief、Plan、Schedule、Evidence、Coverage |
| 质量验证 | 已完成 | Citation、Claim-Evidence、PDF Grounding、Answer Verification |
| 有限 Agent Loop | 已完成 | Retrieval Replan 与 Answer Reflection 均有次数和证据约束 |
| 会话与长期记忆 | 已完成 v1 | 文件会话、SQLite Checkpoint、Memory RAG、Write Gate |
| 个人论文库 | 已完成 MVP | 注册登录、用户隔离、PDF 上传、Personal/Online/Hybrid |
| PDF 视觉理解 | 已完成 v2 | 自动关键页、Figure/Table/`ChartAnalysisSkill`/Formula、真实在线测试 |
| 报告导出 | 已完成 v1 | 中文 Word/PDF 下载，不额外调用 LLM |
| Web、Docker、CI | 已完成基础版 | 演示页、容器、健康检查、GitHub Actions |
| 受控策略进化 | 已完成 v1 | Failure Dataset、候选生成、Promotion Gate、Version Registry；只进入人工审批 |

受控策略进化已完成首次真实在线 A/B：12 次主模型调用、16,150 Token。few-shot 的解析率和总体通过率明显提升，但因逐题回归与 Token 超预算被 Gate 拒绝，证明门控会阻止“平均分变好但局部退化”的负优化。详见 [真实进化测试报告](REAL_EVOLUTION_TEST_REPORT.md)。

## 3. 完整系统架构

下面是架构总览；每个节点的输入、判断逻辑、输出、失败恢复和典型请求路径，详见 [架构模块逐流程详解](ARCHITECTURE_MODULE_GUIDE.md)。

```text
用户
├─ Web Research Console
├─ FastAPI / Swagger
└─ CLI
   ↓
PaperAgentService
├─ Trace ID
├─ 用户与会话身份
├─ PDF 输入准备
├─ 会话记忆 / Checkpoint
└─ LangGraph State 初始化
   ↓
LangGraph 主图
├─ Intent Router
│  ├─ Smalltalk → 本地零 LLM 回答
│  └─ 论文任务 → 继续
├─ Clarification
│  ├─ 明确指代 → 规则恢复
│  ├─ 描述性指代 → 受限语义解析
│  └─ 无法恢复 → 主动澄清
├─ Research Analyzer
│  ├─ L1：简单检索/问答
│  ├─ L2：比较与组合任务
│  └─ L3：复杂研究任务
├─ Query Rewrite / Query Plan / Scheduler
│  ├─ 子查询与依赖
│  ├─ 最大并发限制
│  └─ 非法计划阻断
├─ Retrieval Router
│  ├─ Online
│  │  └─ Tool Router → Registry → Policy → Executor
│  │     ├─ arXiv
│  │     ├─ OpenAlex
│  │     ├─ Crossref
│  │     └─ Semantic Scholar
│  ├─ Personal Library
│  │  └─ Owner-scoped BM25 / Local RAG
│  ├─ Hybrid
│  │  └─ Personal + Online 有界并行
│  └─ PDF Reading
│     ├─ 全文文本
│     └─ 关键页视觉理解
├─ Evidence Store
│  ├─ 类型化论文证据
│  ├─ 页面与来源定位
│  ├─ 去重和规范化
│  └─ Coverage 检查
├─ Skill Router
│  ├─ QA / Summary / Compare / Citation
│  ├─ Literature Review / Paper Critique
│  └─ Figure / Table / Chart / Formula
├─ Generate / Research Writer
├─ Verification Pipeline
│  ├─ Citation Validator
│  ├─ Claim-Evidence Validator
│  ├─ PDF Grounding Validator
│  └─ Answer Verifier
├─ Bounded Recovery
│  ├─ Retrieval Replan：最多 1 次
│  └─ Answer Reflection：最多 1 次且必须已有修复证据
├─ Memory Write Gate
│  ├─ Verification
│  ├─ Value / Stability / Time-sensitive Policy
│  ├─ Dedup / Conflict
│  └─ Write / Merge / Update / Skip
└─ Metrics / Multi-Agent Trace / Stop Reason
   ↓
中文研究回答
├─ 论文证据与引用
├─ LangGraph 执行轨迹
├─ Token / 延迟 / 工具记录
└─ Word / PDF 研究报告
```

## 4. PDF 视觉理解 v2

PDF 能力不是只提取文字。当前流程为：

```text
PDF 问题
→ 是否明确提供页码？
   ├─ 是：使用指定的 1-3 页
   └─ 否：检测视觉意图
      ├─ 普通总结 → 全文文本快速路径
      └─ 图/表/曲线/公式 → 本地图注与查询词选页
→ PyMuPDF 渲染关键页 PNG
→ qwen3.5-ocr 查询感知视觉解析
→ Visual Evidence v2
→ qwen3.7-max-2026-05-17 综合页面文本与视觉证据
→ Figure/Table/Chart/Formula Pydantic Contract
→ PDF Grounding
→ 可追溯回答
```

自动选页为零 LLM 本地逻辑，最多选择 3 页，文本扫描最多 120 页。普通 PDF 请求不会默认发送图片。模糊刻度、颜色、连线或公式上下标必须标记为不确定，不允许凭常识补齐。

真实 GraphRAG 第 4 页视觉测试结果：

| 指标 | 结果 |
|---|---:|
| 测试状态 | 通过 |
| 视觉模型 | qwen3.5-ocr |
| 综合模型 | qwen3.7-max-2026-05-17 |
| Skill | figure_understanding |
| 结构化契约 | FigureUnderstandingOutput，有效 |
| Grounding | 通过 |
| 模型调用 | 2 次 |
| 输入 / 输出 Token | 4,240 / 3,309 |
| 总 Token | 7,549 |
| 总耗时 | 81.668 秒 |

详细记录见 [PDF 视觉理解 v2 报告](PDF_VISUAL_V2_REPORT.md)。

## 5. RAG 与检索设计

PaperAgent 没有把某一种 RAG 方案写死为唯一答案，而是使用评测与门控决定生产路径：

```text
查询
→ Retrieval Scope
   ├─ Online：发现最新或外部论文
   ├─ Personal：只检索用户论文库
   └─ Hybrid：私人材料 + 公开论文
→ Local RAG
   ├─ BM25：关键词与专名稳定
   ├─ MPNet Dense：语义召回
   └─ Gated Hybrid：低置信度时使用 RRF 融合
→ 去重、规范化、重排
→ Evidence Coverage
```

GraphRAG、LightRAG 或其他图结构 RAG 仍保留为候选技术，不作为简历版本的强制依赖。只有固定跨论文全局问题证明现有 Hybrid RAG 不足时，才通过统一评测做小型 PoC 和晋升判断。

## 6. 记忆与数据隔离

| 层级 | 存储 | 作用 |
|---|---|---|
| 最近会话 | 本地文件 | 保存有限对话和研究上下文 |
| LangGraph State | SQLite Checkpointer | 按 `thread_id` 恢复节点状态 |
| 长期研究记忆 | SQLite | 保存经过验证、可复用的研究结论 |
| 论文原始材料 | Personal Library | 保存用户 PDF、文档和 Chunk |
| Dense 缓存 | 项目 `data/cache` | 保存模型与向量，避免重复计算 |

论文库保存 Source Knowledge，长期记忆保存 Derived Research Knowledge。两者都以用户/会话 Owner 隔离；Memory Write Gate 会检查验证状态、价值、稳定性、时效、重复和冲突，不是所有回答都会进入长期记忆。

## 7. 快速运行

### 本机启动

```powershell
Set-Location D:\langgraphproject
conda activate paper_agent
python -m pip install -r requirements.txt
python -m uvicorn app.api:app --host 127.0.0.1 --port 8000
```

打开：

- Research Console：`http://127.0.0.1:8000/`
- Swagger：`http://127.0.0.1:8000/docs`
- Health：`http://127.0.0.1:8000/health`

### Docker 启动

```powershell
Set-Location D:\langgraphproject
docker compose up --build -d
docker compose ps
```

停止：

```powershell
docker compose down
```

### 必要模型配置

```env
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_API_KEY=你的百炼_API_Key
MODEL_NAME=qwen3.7-max-2026-05-17
PDF_VISION_MODEL_NAME=qwen3.5-ocr
PDF_VISION_ENABLED=true
```

不要将 `.env`、API Key、本地论文、SQLite 或模型缓存提交到 Git。

## 8. 推荐演示顺序

### 演示一：零 API 完整轨迹

启动网页后点击“加载示例轨迹”。展示 Research Plan、执行波次、Evidence Store、质量闸门和节点耗时，不依赖网络或模型。

### 演示二：低成本意图短路

输入 `hi`。说明问候不会调用检索或 LLM，体现成本路由。

### 演示三：个人库 + 在线 Hybrid

注册登录、上传 ReAct PDF，选择 Hybrid，然后询问：

> 结合我收藏的 ReAct 论文和在线论文，比较 ReAct 与反思型 Agent 的核心架构和适用场景。

真实参考结果：8 条证据、Personal + arXiv、总耗时 31.71 秒、2 次 LLM、5,717 Token、Answer Verification 通过。详见 [Hybrid 冒烟报告](HYBRID_SMOKE_REPORT.md)。

### 演示四：PDF 图表理解

指定 GraphRAG PDF 或输入图表问题，让系统自动选页，展示视觉任务、页面选择、结构化契约和 Grounding。

### 演示五：报告导出

完成研究任务后点击“下载 Word”或“下载 PDF”。导出复用现有结论和证据，不再次调用模型。

## 9. 测试与验证数据

| 测试 | 结果 | 费用属性 |
|---|---:|---|
| PDF v2 专项、前端与 Prompt | 35/35 通过 | 离线，0 LLM |
| 项目完整单元/集成回归 | 422/422 通过 | 离线，0 LLM |
| PDF 视觉在线冒烟 | 1/1 通过 | 2 次调用，7,549 Token |
| Personal + Online Hybrid | 通过 | 2 次调用，5,717 Token |
| LLM 核心正式评测集 | 27/30 通过，90% | 17 次调用，62,525 Token |

完整测试表格位于 `outputs/test_reports/full_pdf_visual_v2/latest_test_details.csv`。每个测试都在 `scripts/test_case_catalog.py` 中记录用途、通过含义和失败含义。

完整离线回归命令：

```powershell
python -m scripts.run_tests_with_report --output-dir outputs\test_reports\final -- tests
```

真实 PDF 视觉测试必须明确同意图片出站：

```powershell
python -m eval_harness.pdf_vision_smoke --confirm-online --pdf data\papers\2404.16130_graph_rag.pdf --page 4
```

## 10. 技术栈

| 层级 | 技术 |
|---|---|
| Agent 编排 | LangGraph、LangChain |
| 模型 | qwen3.7-max-2026-05-17、qwen3.5-ocr |
| API | FastAPI、Pydantic、Uvicorn |
| 在线数据源 | arXiv、OpenAlex、Crossref、Semantic Scholar |
| 工具协议 | 自研 Tool Layer、MCP |
| RAG | PyPDF、BM25、MPNet/FastEmbed、ONNX Runtime、RRF |
| PDF 视觉 | PyMuPDF、页面 PNG、多模态消息、Pydantic Contracts |
| 数据与记忆 | SQLite、JSON、NumPy 缓存 |
| 前端 | HTML、CSS、原生 JavaScript |
| 工程化 | Docker、Docker Compose、GitHub Actions |
| 测试与评测 | Pytest、JSON/CSV/Excel-ready Reports |

## 11. 项目差异化与面试重点

建议重点讲四件事：

1. **Graph Engineering**：LangGraph 节点不是形式化拆分，而是承载条件路由、证据状态、失败恢复和停止原因。
2. **Evidence Engineering**：答案必须经过 Evidence Store、Coverage、Citation、Claim 和 Grounding，而不是只依赖 Prompt 说“不要幻觉”。
3. **成本受控 Agent Loop**：Smalltalk 零 LLM，自动选页零 LLM，Replan/Reflection 最多一次，所有调用记录 Token 和耗时。
4. **Private + Public Research**：个人论文库与公开论文并行检索，兼顾用户私有知识和最新外部研究。

简历描述示例：

> 基于 LangGraph 构建证据驱动科研 Research Agent，支持多源论文检索、用户级 Local/Hybrid RAG、MCP 工具治理、PDF 图表视觉理解、长期研究记忆与有限失败恢复；设计 Coverage/Citation/Claim/Grounding 多级验证链路，完整离线回归 422/422 通过，并通过真实 Personal+Online 与 PDF Vision 在线冒烟。

## 12. 已知边界

- 自动视觉选择以页面为单位，尚未裁剪单个图表区域。
- 主模型读取结构化视觉证据，没有再次直接接收原始页面图片。
- 个人库 Dense 索引、团队 RBAC、邮件验证和 Refresh Token 未进入简历版 MVP。
- GraphRAG/LightRAG 尚未作为生产知识库实现，目前采用可评测选型而非预设答案。
- 在线数据源和百炼模型受网络、限流、配额与第三方变化影响。
- SQLite 适合当前单机演示；真正多实例部署需要数据库、对象存储和缓存升级。

## 13. 后续工作优先级

### 发布前必须完成

1. 补充 3-5 张清晰的 Web 演示截图。
2. 在全新环境执行一次 README 冷启动检查。
3. 检查 GitHub Actions 和 Docker 镜像最终状态。
4. 整理简历项目描述与 3 分钟面试讲解脚本。

### 暂不建议继续开发

- 完整 GraphRAG/LightRAG 平台化实现；
- 八角色或无限循环 Multi-Agent；
- 全篇 PDF 无差别视觉扫描；
- 自动在线自进化和模型自修改；
- Team/Organization/RBAC 企业功能；
- 大规模研究型评测矩阵。

这些方向可以保留在 Roadmap，但不应阻碍当前简历版本交付。

## 14. 相关文档

- [README](../README.md)
- [后续路线图](ROADMAP.md)
- [PDF 视觉理解 v2 报告](PDF_VISUAL_V2_REPORT.md)
- [Personal + Online Hybrid 冒烟报告](HYBRID_SMOKE_REPORT.md)
- [测试报告使用说明](../scripts/TEST_REPORTS.md)
