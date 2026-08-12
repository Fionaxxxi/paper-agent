# 跨来源统一重排与元数据解析

## 目标与流程

旧 `multi` 按来源顺序合并，并在达到 Top K 时立即截断。`deterministic_cross_source_v1` 先完整去重，再统一评分，最后截取 Top K，全程不调用 LLM。

```text
arXiv / OpenAlex 原始候选
→ DOI、entry_id、PDF URL、标题去重
→ 合并来源与各来源原始排名
→ 本地元数据一致性检查
→ 计算可解释相关性分数
→ 全来源统一排序
→ 截取 Top K
```

## 评分组成

```text
45% 标题查询覆盖率
+ 20% 摘要查询覆盖率
+ 8% 完整查询短语命中
+ 15% 最佳来源倒数排名
+ 4% 跨来源重复确认奖励
+ 3% 对数归一化引用信号
+ 5% 元数据质量
```

论文同时保存 `ranking_score`、`ranking_signals`、`sources`、`source_ranks` 和 `metadata_warnings`，便于审计。中文按单字、英文按词确定性切分，常见英文停用词不参与覆盖率。

## 元数据校验

v1 无需联网即可识别标题、稳定身份或摘要缺失，arXiv ID 冲突，年份非法，以及相同身份的跨来源标题冲突。在线金标准评测还会识别 `GOLD_TITLE_CONFLICT`：稳定 ID 命中但标题与金标准严重不一致时，不再计入 Recall、MRR 或 nDCG。

v2 增加确定性的元数据来源解析：

```text
收集每个重复身份的来源证据
→ 规范化 DOI 与 arXiv ID
→ 若存在原生 arXiv 响应，以其作为该 arXiv 身份的权威证据
→ 修复冲突标题或缺失字段，并保留修复明细
→ 若只有二级来源声称 arXiv DOI，则标为待确认
→ 二级身份声明同时与查询标题严重不符时，隔离出排名候选
→ 输出规范身份、解析状态、处理动作、修复与隔离计数
```

这里的“权威”有严格边界：目前只把原生 arXiv 响应视为 arXiv 身份的权威证据；OpenAlex 的 DOI 字段属于二级身份声明。非 arXiv DOI 尚未接入 Crossref 等规范来源，因此不会被伪装成已经权威确认。

## 开关与回滚

```env
MULTI_SOURCE_RERANK_ENABLED=false
MULTI_SOURCE_METADATA_VERIFICATION_ENABLED=false
```

- `false`：旧 `source_priority`；
- 只开启重排：`deterministic_cross_source_v1`；
- 同时开启元数据校验：`deterministic_cross_source_verified_v2`；
- 注入按原生 ID 获取的规范元数据证据：`canonical_authority_verified_v3`。
- 仅在 `RETRIEVAL_MODE=multi` 或 `multi_source` 时生效；
- 单来源检索不受影响。

两个开关相互独立，关闭元数据校验即可回滚到 v1；关闭重排即可回滚到旧来源优先策略。

## 缓存回放结果

使用在线评测集 v1.0.0 的 20 个问题和同一份 40 个来源响应：

| 配置 | Recall@5 | MRR@5 | nDCG@5 | API 调用 | LLM Token |
|---|---:|---:|---:|---:|---:|
| 旧 multi | 55.00% | 45.42% | 47.81% | 0（40 个缓存命中） | 0 |
| multi_rerank | 60.00% | 57.50% | 58.15% | 0（40 个缓存命中） | 0 |
| multi_verified_rerank | 60.00% | 57.50% | 58.15% | 0（40 个缓存命中） | 0 |

2026-08-11 的 v3 候选实验只复核两份独立快照中被 v2 隔离过的 13 个 arXiv 身份。12 个取得原生记录，1 个原生查无；规范证据通过 `paper.lookup.arxiv` 工具取得并缓存，不调用 LLM。两份快照的 Recall@5 均从 60.00% 提升到 65.00%，MRR@5 均从 57.50% 提升到 62.50%；隔离数分别从 8 降到 0、从 13 降到 1。结果证明“标题与查询词法重合低”不能作为身份冲突证据，身份验证与相关性排序必须分离。

v3 当前仍是候选能力，不受 `MULTI_SOURCE_METADATA_VERIFICATION_ENABLED` 默认开关控制。晋升前还需要更多独立快照、普通 DOI 规范来源候选（例如 Crossref）的同口径评测，以及对原生查无、网络失败和来源冲突分别设定恢复策略。

2026-08-12 增加第三份完整独立快照后，v3 再次得到 Recall@5 65.00%、MRR@5 62.50%、nDCG@5 65.31%，逐题回归为 0。三快照自动门槛已经通过，但现有生产开关同时覆盖多种元数据行为，因此不会直接切换；下一步先拆分 arXiv authority 开关并评测普通 DOI provider，再进行受控启用。

arXiv authority 现由 `ARXIV_AUTHORITY_VERIFICATION_ENABLED` 独立控制，默认关闭。开启后只查询缺少同 ID 原生证据的二级声明；成功响应缓存，超时、SSL 等执行失败不缓存，也不作为负证据。普通 DOI provider 复用 `paper.lookup` 接口，Crossref 首轮 20 DOI 候选评测为 20/20 匹配，但尚未进入生产重排。

普通 DOI authority 已完成最小污染挑战集验收后冻结：只在 `DOI_AUTHORITY_VERIFICATION_ENABLED` 开启时参与规范验证；明确查无只警告，网络失败不缓存，均不自动隔离普通 DOI。

多来源搜索支持 `MULTI_SOURCE_PARALLEL_ENABLED` 有界并行。同步 provider 通过最多 `MULTI_SOURCE_MAX_WORKERS` 个线程并发执行，但结果始终按 `MULTI_SOURCE_PROVIDERS` 配置顺序收集，因此并发完成顺序不会改变去重和重排语义。单来源不创建线程池，开关默认关闭。

复杂查询还支持独立的 `MULTI_QUERY_PARALLEL_ENABLED` 子查询并行开关，最大并发由 `MULTI_QUERY_MAX_WORKERS` 控制，默认同样关闭。子查询结果按查询规划顺序收集；在来源级并行通过真实网络门槛前，不建议同时开启两级并行，以免放大限流。

重排使 Reflexion 金标准论文从 Top 5 外升至第 1，并提升 RAG、LightRAG 和 DPR 排名；20 题没有 Recall 或 MRR 退化。v2 在保持所有质量指标不变的同时隔离 8 条“未经原生来源确认且标题与查询明显不符”的候选，其中包括此前进入 Top 3 的异常 Chain-of-Thought 记录；本轮没有发生实际字段修复，因为进入同一身份组的原生 arXiv 记录本身已位于主记录。

## 晋升门槛

- Recall@5 不低于旧 multi，MRR/nDCG 稳定提升；
- 不新增 LLM Token 或排序 API 调用；
- 元数据冲突论文不得进入高排名；
- 开关关闭时原图保持稳定；
- 在至少两次独立在线快照上复现收益。
