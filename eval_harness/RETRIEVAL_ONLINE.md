# 在线论文检索评测

这套评测用于比较 `arxiv`、`openalex`、`multi`、`multi_rerank` 和 `multi_verified_rerank` 在同一批论文问题上的检索质量、延迟与可靠性。它与离线能力基准分开运行，不进入默认 CI，也不会在缺少凭据时偷偷消耗匿名 OpenAlex 额度。

## 当前评测集

- 文件：`eval_harness/datasets/retrieval_online_v1.json`
- 版本：`1.0.0`
- 数量：20 题
- 覆盖：中英文查询，以及 RAG、Agent、工具使用、长上下文、稠密检索和图检索等主题。
- 金标准：每题至少标注一篇相关论文，并保存标题、arXiv ID、DOI、相关性等级和必要覆盖维度。

当前 20 题是第一版种子集，适合验证评测链路和观察明显差异，但还不能代表所有学术问题。扩充时必须升级数据集版本，并保留旧版本供历史对比。

## 匹配与指标

论文先按 DOI、arXiv ID、规范化标题建立身份键；任一稳定身份匹配即视为命中金标准。标题只作为 DOI/arXiv ID 缺失时的后备匹配。

- `Recall@K = 前 K 条命中的不同金标准论文数 / 金标准论文总数`：越高表示漏掉的相关论文越少。
- `Precision@K = 前 K 条命中的不同金标准论文数 / K`：越高表示前排无关论文越少；返回不足 K 条时分母仍为 K。
- `MRR@K = 1 / 第一篇相关论文的排名`：前 K 条未命中则为 0，越高表示有效论文出现越早。
- `nDCG@K = DCG@K / 理想 DCG@K`：使用相关性等级计算，兼顾命中、排名位置和分级相关性。
- `dimension_coverage_pct = 已命中的必要维度数 / 必要维度总数 × 100%`：检查结果是否覆盖问题需要的研究角度。
- `duplicate_rate_pct = (合并前数量 - 合并后数量) / 合并前数量 × 100%`：反映多来源冗余，不能脱离 Recall 单独判断。
- `failure_rate_pct`：网络、超时、限流等执行失败占比，失败不会伪装成正常空结果。
- `empty_result_rate_pct`：最终零篇论文的问题占比。
- `P50/P95 network latency`：真实来源响应延迟的中位数和尾部延迟。

平均质量指标以完整问题数为分母。只要存在失败题，报告必须标为部分完成，不能与无失败运行直接横比。

## 公平性与成本控制

```text
每个问题
→ arXiv 原始响应只请求一次
→ OpenAlex 原始响应只请求一次（需要 API Key）
→ 五种配置复用同一响应快照
→ multi 统一身份去重并限制为相同 K
→ 保存逐题排名、命中、错误、延迟和缓存状态
```

`multi_rerank` 与 `multi` 复用相同来源响应，只把“按来源顺序截断”替换为“完整去重、统一评分、最后截断”。`multi_verified_rerank` 再增加来源证据解析、字段修复和低可信候选隔离。三者使用同一批候选，因此 A/B 不新增 API 调用。

成功响应按“快照 ID + 数据集版本 + 来源 + case id”缓存。未指定 `--snapshot-id` 时兼容旧目录；显式快照写入 `snapshots/<id>`，已有快照默认拒绝覆盖，只有 `--resume-snapshot` 可以复用成功响应并补取失败项。每次续跑都追加到快照清单，累计实际 API 调用和缓存命中。arXiv 使用跨问题全局间隔，HTTP 429 触发有限冷却重试；失败响应不缓存。

OpenAlex 默认要求 `OPENALEX_API_KEY`。未配置时记录 `MISSING_API_KEY / skipped`，实际调用数为 0。只有显式传入 `--allow-openalex-without-key` 才允许匿名评测。

## 运行命令

```powershell
# 完整三配置评测
D:\miniconda3\envs\paper_agent\python.exe -m eval_harness.retrieval_online

# 加入跨来源重排候选对照
D:\miniconda3\envs\paper_agent\python.exe -m eval_harness.retrieval_online `
  --profiles arxiv,openalex,multi,multi_rerank,multi_verified_rerank

# 创建一份不会覆盖旧响应的独立快照
D:\miniconda3\envs\paper_agent\python.exe -m eval_harness.retrieval_online `
  --snapshot-id 2026-08-11-b `
  --profiles arxiv,openalex,multi,multi_rerank,multi_verified_rerank

# 限流或网络中断后，只补取失败项
D:\miniconda3\envs\paper_agent\python.exe -m eval_harness.retrieval_online `
  --snapshot-id 2026-08-11-b --resume-snapshot `
  --profiles arxiv,openalex,multi,multi_rerank,multi_verified_rerank

# 单题网络冒烟测试
D:\miniconda3\envs\paper_agent\python.exe -m eval_harness.retrieval_online --case-limit 1 --refresh

# 限流后续跑：成功题读取缓存
D:\miniconda3\envs\paper_agent\python.exe -m eval_harness.retrieval_online `
  --arxiv-interval 10 --rate-limit-cooldown 60 --rate-limit-retries 1
```

## 输出与解读

默认输出目录 `eval_harness/reports/retrieval_online/` 包含：

- `latest_retrieval_online.json`：完整可审计报告；
- `latest_retrieval_summary.csv`：来源配置总览；
- `latest_retrieval_cases.csv`：逐题指标与失败明细；
- `latest_retrieval_papers.csv`：逐篇排名、身份和金标准匹配；
- `provider_cache/`：成功的原始来源响应缓存。

每次结论至少同时报告 Recall@K、MRR@K、失败率、空结果率、P95 延迟、实际请求数和缓存命中数。OpenAlex 被跳过或任一配置存在失败时，不得宣称 multi 优于或劣于单来源。

## 2026-08-05 阶段运行

20 题续跑后，arXiv 为 `Recall@5 = 0.5500`、`MRR@5 = 0.4542`，最终网络失败为 0，2 题正常返回零篇。OpenAlex 20 题因缺少 API Key 全部跳过；multi 因只有 arXiv 可用而质量指标与 arXiv 相同。这是用于验证评测系统的阶段报告，不是多数据源选型结论。

2026-08-10 增加标题冲突门控后，旧 `multi` 为 Recall@5 55.00%、MRR@5 45.42%，`multi_rerank` 为 Recall@5 60.00%、MRR@5 57.50%。质量提升，但仍有一条 `GOLD_TITLE_CONFLICT` 异常记录进入 Top 3。

2026-08-11 增加元数据来源解析后，`multi_verified_rerank` 保持 Recall@5 60.00%、MRR@5 57.50%、nDCG@5 58.15%，并把上述异常记录及另外 7 条低可信、低查询一致性二级身份声明隔离出排序。本次复用 40 个缓存响应，实际 API 调用与 LLM Token 均为 0。隔离动作必须和逐题质量一起评估，不能把“删得更多”单独视为改进。

2026-08-11 第二份独立快照首次运行时 arXiv 仅成功 10/20，OpenAlex 成功 20/20；通过显式续跑补齐后，两来源均为 20/20。候选快照中 `multi_verified_rerank` 再次得到 Recall@5 60.00%、MRR@5 57.50%、nDCG@5 58.15%，逐题质量回归为 0。但隔离候选从 8 条变为 13 条，只有 6 条稳定重合，Jaccard 稳定度为 40%，低于 80% 门槛；新增项包含可能有研究价值的相关论文，因此 v2 继续保持默认关闭，下一步必须使用规范元数据来源验证，而不能继续加严词法隔离规则。

同日完成规范 arXiv ID 候选重放：从两份快照的 v2 隔离记录中提取 13 个唯一身份，通过 `paper.lookup.arxiv` 获取 12 条原生记录，另有 1 条原生查无。v3 在两份快照上都把 Recall@5 从 60.00% 提升到 65.00%、MRR@5 从 57.50% 提升到 62.50%；nDCG@5 分别提升到 63.15% 和 65.31%，隔离数从 8/13 降到 0/1。本实验不重新搜索论文、不调用 LLM；成功规范响应缓存复用，网络失败不缓存且不能视为查无。

2026-08-12 第三份独立快照一次采集完整成功，arXiv 与 OpenAlex 均为 20/20。v2 再次得到 Recall@5 60.00%、MRR@5 57.50%；注入相同规范身份缓存后，v3 得到 Recall@5 65.00%、MRR@5 62.50%、nDCG@5 65.31%，隔离 1 条，逐题质量回归为 0。三快照自动门槛检查通过：快照数、完整性、规范身份覆盖率与逐题无回归均满足要求；该晋升结论仅适用于 arXiv 规范身份候选，不代表普通 DOI 校验已经完成。

普通 DOI 首轮候选评测从三份快照共同稳定出现的非 arXiv DOI 中固定抽取 20 条，通过 `paper.lookup.crossref` 查询：成功覆盖 20/20、标题匹配 20/20、标题冲突 0、查无 0、失败 0，实际 API 调用 20，LLM Token 0。失败结果不缓存。本轮只验证工具契约和初步覆盖，不作为 Crossref 已胜出或可默认启用的结论。

普通 DOI 第二轮使用相同三份快照形成 51 条稳定总体，按 DOI 前缀轮转抽取 40 条、覆盖 19 个前缀，同时通过统一 `paper.lookup` 比较 Crossref 与 Semantic Scholar。Crossref 明确响应 40/40，其中标题匹配 38、查无 2、失败 0；Semantic Scholar 匿名访问明确响应 23/40，其中匹配 18、冲突 2、查无 3、限流失败 17。双方可比的 19 条标题中 18 条一致（94.74%）。当前结论只证明 Crossref 在现有网络配置下更稳定；Semantic Scholar 需配置 API Key 后复测，429 必须记录为 `RATE_LIMITED`，不得合并到查无率。

联合 canonical 重放进一步覆盖三份快照中的全部 65 个普通 DOI，并与 13 个 arXiv authority 合并。78/78 身份均取得明确结果，缓存续跑没有新增 API 或 LLM 调用；联合版相对 v2 的 Recall@5 为 65%（+5pp）、MRR@5 为 62.5%（+5pp），三快照逐题回归为 0。隔离增量对照表明这些质量提升全部来自已验证的 arXiv canonical：Crossref 相对仅 arXiv 版本的 Recall/MRR/nDCG 和 Top-5 排名变化均为 0。Crossref 查无只作为覆盖警告，不作为普通 DOI 的自动隔离依据。

正式晋升必须满足：OpenAlex Key 已配置、所有配置使用同一数据集版本、失败状态已消除、逐题结果完整保存，并且元数据冲突论文不进入高排名。
