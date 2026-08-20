# Personal + Online Hybrid 真实冒烟报告

测试日期：2026-08-20

## 测试目标

验证一条真实链路可以同时使用个人 PDF 全文、arXiv 在线论文和当前主模型，并经过现有 LangGraph 验证与失败恢复节点。

## 测试输入

- 个人库论文：ReAct 原论文（arXiv:2210.03629）；
- 查询：结合个人库 ReAct 原论文和在线论文，比较 ReAct 与反思型 Agent 的核心架构、证据边界和适用场景；
- 范围：`hybrid`；
- 主模型：`qwen3.7-max-2026-05-17`；
- 数据、索引、会话与长期记忆均隔离在 `outputs/hybrid_smoke`。

## 结果

| 指标 | 结果 | 说明 |
|---|---:|---|
| 完整链路 | 通过 | Personal、arXiv、生成和验证均完成 |
| 论文证据 | 8 条 | 合并去重后进入回答上下文 |
| 证据来源 | personal_library + arxiv | Private + Public 均实际命中 |
| 检索耗时 | 2.65 秒 | 两类来源受控并行 |
| 总耗时 | 31.71 秒 | 包含生成和一次 Reflection |
| LLM 调用 | 2 次 | Generate 1 次，Answer Reflection 1 次 |
| Token | 5717 | Generate 3364，Reflection 2353 |
| Answer Verification | 通过 | Reflection 后最终得分 1.0 |
| 工具失败 | 0 | 两次在线检索均成功 |

## 暴露的问题与处理

1. arXiv 候选出现 withdrawn 论文：本轮已增加确定性过滤，并额外拉取候选用于补足 Top-K，不增加 LLM 调用。
2. Reflection 占用 2353 Token，约为本次 Token 的 41%：当前确实修复了初始答案，因此不直接关闭；后续只需优化触发条件，不再建设大型评测。
3. L2 比较目前只执行 Answer Verification，Citation/Claim Validator 仍按 L3 策略关闭：属于现有等级策略，不影响本次冒烟通过，但可作为后续报告质量增强候选。

## 一键复跑

```powershell
conda activate paper_agent
python -m scripts.run_hybrid_online_smoke --confirm-online
```

该命令会访问网络并消耗真实模型 Token；不传 `--confirm-online` 时脚本会拒绝执行。
