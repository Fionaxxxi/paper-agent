# 跨来源统一重排 v1

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

当前无需联网即可识别标题、稳定身份或摘要缺失，arXiv ID 冲突，年份非法，以及相同身份的跨来源标题冲突。在线金标准评测还会识别 `GOLD_TITLE_CONFLICT`：稳定 ID 命中但标题与金标准严重不一致时，不再计入 Recall、MRR 或 nDCG。

本地校验无法证明单一来源的 DOI 与标题是否属于同一论文。2026-08-10 回放中，一条 OpenAlex 异常 Chain-of-Thought 记录仍进入重排 Top 3，虽然已被评测标记且不计为相关命中。因此 v1 暂不默认开启，后续需要 DOI/arXiv ID 权威元数据解析器或可信来源交叉确认。

## 开关与回滚

```env
MULTI_SOURCE_RERANK_ENABLED=false
```

- `false`：旧 `source_priority`；
- `true`：`deterministic_cross_source_v1`；
- 仅在 `RETRIEVAL_MODE=multi` 或 `multi_source` 时生效；
- 单来源检索不受影响。

权威元数据门槛完成前，建议保持 `false`，仅在实验环境开启。

## 缓存回放结果

使用在线评测集 v1.0.0 的 20 个问题和同一份 40 个来源响应：

| 配置 | Recall@5 | MRR@5 | nDCG@5 | API 调用 | LLM Token |
|---|---:|---:|---:|---:|---:|
| 旧 multi | 55.00% | 45.42% | 47.81% | 0（40 个缓存命中） | 0 |
| multi_rerank | 60.00% | 57.50% | 59.06% | 0（40 个缓存命中） | 0 |

重排使 Reflexion 金标准论文从 Top 5 外升至第 1，并提升 RAG、LightRAG 和 DPR 排名；20 题没有 Recall 或 MRR 退化。

## 晋升门槛

- Recall@5 不低于旧 multi，MRR/nDCG 稳定提升；
- 不新增 LLM Token 或排序 API 调用；
- 元数据冲突论文不得进入高排名；
- 开关关闭时原图保持稳定；
- 在至少两次独立在线快照上复现收益。
