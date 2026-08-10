# 在线论文检索评测

这套评测用于比较 `arxiv`、`openalex`、`multi` 和 `multi_rerank` 在同一批论文问题上的检索质量、延迟与可靠性。它与离线能力基准分开运行，不进入默认 CI，也不会在缺少凭据时偷偷消耗匿名 OpenAlex 额度。

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
→ 四种配置复用同一响应快照
→ multi 统一身份去重并限制为相同 K
→ 保存逐题排名、命中、错误、延迟和缓存状态
```

`multi_rerank` 与 `multi` 复用相同来源响应，只把“按来源顺序截断”替换为“完整去重、统一评分、最后截断”，因此排序 A/B 不新增 API 调用。

成功响应按“数据集版本 + 来源 + case id”缓存。默认复用缓存，`--refresh` 强制重取。arXiv 使用跨问题全局间隔，HTTP 429 触发有限冷却重试；失败响应不缓存，以便后续续跑。

OpenAlex 默认要求 `OPENALEX_API_KEY`。未配置时记录 `MISSING_API_KEY / skipped`，实际调用数为 0。只有显式传入 `--allow-openalex-without-key` 才允许匿名评测。

## 运行命令

```powershell
# 完整三配置评测
D:\miniconda3\envs\paper_agent\python.exe -m eval_harness.retrieval_online

# 加入跨来源重排候选对照
D:\miniconda3\envs\paper_agent\python.exe -m eval_harness.retrieval_online `
  --profiles arxiv,openalex,multi,multi_rerank

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

2026-08-10 增加标题冲突门控后，旧 `multi` 为 Recall@5 55.00%、MRR@5 45.42%，`multi_rerank` 为 Recall@5 60.00%、MRR@5 57.50%。质量提升，但仍有一条 `GOLD_TITLE_CONFLICT` 异常记录进入 Top 3，因此暂不默认开启。

正式晋升必须满足：OpenAlex Key 已配置、所有配置使用同一数据集版本、失败状态已消除、逐题结果完整保存，并且元数据冲突论文不进入高排名。
