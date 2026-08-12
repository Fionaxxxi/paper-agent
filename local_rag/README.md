# 本地 RAG 可行性验证

本目录只提供可插拔的全文检索准备层，不改变实时 arXiv/OpenAlex 主流程，也不预先绑定向量库或 GraphRAG 产品。

## 放置论文

将用户选择的 5～10 篇测试论文放入 `data/papers/`。PDF 文件被 Git 忽略，不会随代码提交。

## 三层数据原则

```text
原始层：PDF + SHA-256 + 来源版本
→ 解析层：逐页文本 + Chunk + Parser/Chunker 版本
→ 索引层：BM25 / Dense / Graph 等可删除、可重建索引
```

PDF 哈希、Parser 版本或 Chunker 版本变化时，只重建受影响论文。Embedding 或检索技术变化时只替换索引层。

## 人工标注

复制 `eval_harness/datasets/rag_annotation_template.json`，为每个问题填写参考答案、支持证据、PDF 页码和来源路径。第一轮建议 5～10 篇论文、15～20 个问题。

## 当前边界

- 已有逐页 `PyPDFPageParser`，不包含 OCR 和表格识别。
- 已有固定窗口 Chunker，作为最简单基线。
- 已有不依赖外部库的 BM25 内存基线，采用英文词与中文单字/双字混合分词；它只用于建立可审计下限，不是最终选型。
- 首次 16 题精确 Chunk 评测得到 Recall@5 18.75%、MRR@5 10.94%、nDCG@5 12.89%，主要暴露中文问题与英文全文的词汇鸿沟。
- 尚未建立持久化知识库或向量索引。后续先对照确定性中英查询改写，再实现 Dense，通过同一评测决定是否增加 Hybrid 或图检索。
