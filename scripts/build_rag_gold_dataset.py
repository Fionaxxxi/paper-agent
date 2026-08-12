"""由人工题目与证据锚点构建首版本地全文 RAG 金标准。"""

from __future__ import annotations

import json
from pathlib import Path

from eval_harness.rag_eval_models import RAGEvalDataset
from local_rag.chunker import FixedWindowChunker
from local_rag.parser import PyPDFPageParser


SPECS = [
    ("rag_architecture", "RAG-Sequence 与 RAG-Token 使用检索文档的方式有什么区别？", "method", "simple", "RAG-Sequence 在生成整个目标序列时使用同一篇检索文档；RAG-Token 允许每个目标 token 基于不同文档生成。", "rag_2005_11401", 3, "RAG-Sequence, the model uses the same document"),
    ("rag_qa_results", "RAG 论文中 RAG-Sequence 在 Natural Questions 测试集上的分数是多少？", "experiment", "simple", "表 1 报告 RAG-Sequence 在 Natural Questions 上取得 44.5。", "rag_2005_11401", 6, "RAG-Seq. 44.5"),
    ("dpr_core_method", "DPR 如何表示问题和文本段并计算二者相似度？", "method", "simple", "DPR 使用两个独立的 BERT 编码器分别把问题和文本段映射为稠密向量，并以向量点积作为相似度。", "dpr_2004_04906", 3, "similarity between the question and the passage"),
    ("dpr_gain", "DPR 相比强 Lucene-BM25 基线的 Top-20 文本段检索准确率提升幅度是多少？", "experiment", "simple", "论文摘要报告，在多种开放域问答数据集上，DPR 的 Top-20 文本段检索准确率绝对提升约 9%～19%。", "dpr_2004_04906", 1, "9%–19% absolute"),
    ("selfrag_tokens", "Self-RAG 定义了哪四类 reflection token，它们分别判断什么？", "method", "complex", "四类分别是 Retrieve（是否检索）、ISREL（文本段是否相关）、ISSUP（输出是否被证据支持）和 ISUSE（回答总体是否有用）。", "self_rag_2310_11511", 4, "Four types of reflection tokens"),
    ("selfrag_ablation", "Self-RAG 消融实验中，移除 Critic 后 PopQA、PubHealth 和 ASQA 的结果分别是多少？", "experiment", "complex", "No Critic 消融在 PopQA、PubHealth 和 ASQA 上分别为 42.6、72.0 和 18.1。", "self_rag_2310_11511", 9, "No Critic C 42.6 72.0 18.1"),
    ("graphrag_problem", "GraphRAG 论文认为传统 vector RAG 为什么不适合全局 sensemaking 问题？", "limitation", "simple", "传统 vector RAG 擅长答案局部集中在少量记录中的问题，但全局 sensemaking 需要理解整个数据集及其跨实体、地点和事件的连接，因此局部相似度检索不足。", "graph_rag_2404_16130", 2, "vector RAG approaches do not support sensemaking queries"),
    ("graphrag_pipeline", "GraphRAG 从源文档到全局答案的主要处理链路是什么？", "method", "complex", "源文档先被切成文本块，抽取实体与关系形成知识图谱，再检测图社区并生成社区摘要；查询时由社区摘要产生局部回答，最后汇总为全局答案。", "graph_rag_2404_16130", 4, "Source Documents"),
    ("lightrag_retrieval", "LightRAG 的双层检索分别面向什么信息？", "method", "complex", "低层检索聚焦具体实体及其关系，高层检索聚焦更抽象的主题或概念；二者结合以兼顾局部细节与全局语义。", "light_rag_2410_05779", 4, "Low-Level Retrieval"),
    ("lightrag_incremental", "LightRAG 如何支持知识库增量更新？", "method", "complex", "新文档经过与既有文档相同的图索引步骤，随后把新旧图的节点集合与边集合分别取并集，从而避免完全重建整个外部数据库。", "light_rag_2410_05779", 4, "Fast Adaptation to Incremental Knowledge Base"),
    ("react_interleave", "ReAct 的核心工作模式是什么？", "method", "simple", "ReAct 让语言模型以交错方式生成推理轨迹和任务动作：推理用于形成、跟踪和调整计划，动作则与外部知识源或环境交互获取信息。", "react_2210_03629", 1, "interleaved manner"),
    ("react_alfworld", "ReAct 在 ALFWorld 与 WebShop 上相对基线分别取得多大的绝对成功率提升？", "experiment", "simple", "论文摘要报告，ReAct 在 ALFWorld 和 WebShop 上分别取得 34% 和 10% 的绝对成功率提升。", "react_2210_03629", 1, "34% and 10%"),
    ("reflexion_memory", "Reflexion 如何组织短期记忆与长期记忆？", "memory", "complex", "轨迹历史作为短期记忆，Self-Reflection 输出存入长期记忆；两者共同提供当前任务细节和跨尝试提炼的经验。", "reflexion_2303_11366", 5, "trajectory history serves as the short-term"),
    ("reflexion_humaneval", "Reflexion 在 HumanEval Python 上的总体准确率是多少，基线是多少？", "experiment", "simple", "表 2 中 HumanEval Python 的语言模型基线为 0.80，加入 Reflexion 后为 0.91。", "reflexion_2303_11366", 8, "HumanEval (PY) 0.80 0.91"),
    ("agent_memory_risks", "LLM Agent Survey 指出记忆写入需要处理哪两个问题？", "memory", "simple", "需要处理与已有记忆相似造成的记忆重复，以及存储达到上限时的记忆溢出和删除问题。", "agent_survey_2308_11432", 9, "memory duplicated"),
    ("agent_replanning", "LLM Agent Survey 为什么认为复杂任务不能只依赖初始计划？", "planning", "complex", "因为一开始就生成无瑕计划很困难，且不可预测的环境转移可能让初始计划无法执行；因此 Agent 应根据外部反馈迭代修订计划。", "agent_survey_2308_11432", 12, "simply following the initial plan often leads to fail"),
]


def build_dataset(papers_dir: Path, output: Path) -> Path:
    sources = json.loads((papers_dir / "corpus_sources.json").read_text(encoding="utf-8"))
    by_id = {item["document_id"]: item for item in sources["documents"]}
    parser, chunker = PyPDFPageParser(), FixedWindowChunker()
    parsed = {}
    chunks = {}
    for document_id, source in by_id.items():
        pages = parser.parse(papers_dir / source["filename"], document_id)
        parsed[document_id] = {page.page_number: page for page in pages}
        chunks[document_id] = chunker.chunk(pages)

    cases = []
    for case_id, question, category, difficulty, answer, document_id, page_number, anchor in SPECS:
        page = parsed[document_id][page_number]
        normalized = page.text.replace("−", "-").replace("–", "-")
        normalized_anchor = anchor.replace("−", "-").replace("–", "-")
        start = normalized.find(normalized_anchor)
        if start < 0:
            raise ValueError(f"证据锚点未找到：{case_id} / {anchor}")
        raw_start = max(0, start - 180)
        raw_end = min(len(page.text), start + len(anchor) + 280)
        candidates = [chunk for chunk in chunks[document_id] if chunk.page_start == page_number and chunk.char_start <= start < chunk.char_end]
        if not candidates:
            raise ValueError(f"证据未映射到 chunk：{case_id}")
        source = by_id[document_id]
        cases.append({
            "id": case_id, "question": question, "language": "zh", "category": category,
            "difficulty": difficulty, "reference_answer": answer,
            "evidence": [{
                "document_id": document_id, "chunk_id": candidates[0].chunk_id,
                "page_start": page_number, "page_end": page_number,
                "quote": page.text[raw_start:raw_end].strip(),
                "source_path": f"data/papers/{source['filename']}", "relevance_grade": 3,
            }],
        })
    payload = {"dataset_name": "PaperAgent 本地全文 RAG 人工金标准 v1", "dataset_version": "1.0.0", "description": "基于 8 篇真实论文全文人工编写并逐页核验证据的 16 题首版金标准。", "corpus_version": sources["corpus_version"], "k_values": [1, 3, 5], "cases": cases}
    validated = RAGEvalDataset.model_validate(payload)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(validated.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")
    return output


if __name__ == "__main__":
    result = build_dataset(Path("data/papers"), Path("eval_harness/datasets/rag_gold_v1.json"))
    print(f"已生成：{result}")
