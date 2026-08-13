"""构建不参与术语表设计的本地 RAG 保留金标准。"""

from __future__ import annotations

import json
import re
from pathlib import Path

from eval_harness.rag_eval_models import RAGEvalDataset
from local_rag.chunker import FixedWindowChunker
from local_rag.parser import PyPDFPageParser


SPECS = [
    ("holdout_rag_decoding", "开放域问答实验中，RAG-Token 和 RAG-Sequence 各使用多少篇召回文档？", "implementation", "simple", "开放域问答测试中，RAG-Token 使用 15 篇召回文档；RAG-Sequence 使用 50 篇。", "rag_2005_11401", 17, "using 15 retrieved documents"),
    ("holdout_dpr_corpus", "DPR 把英文维基百科切成什么样的基本检索单元，最终得到多少个？", "implementation", "simple", "DPR 将文章切成互不重叠的 100 词文本块，并在每块前加入文章标题和 [SEP]，最终得到 21,015,324 个 passage。", "dpr_2004_04906", 4, "21,015,324 passages"),
    ("holdout_selfrag_threshold", "Self-RAG 的检索阈值增大时，检索频率和不同任务的性能如何变化？", "analysis", "complex", "阈值 δ 越大，检索越少；少检索造成的性能下降在 PubHealth 较小、在 PopQA 较大。", "self_rag_2310_11511", 10, "larger δ results in less retrieval"),
    ("holdout_graphrag_directness", "GraphRAG 评测中的 Directness 衡量什么，为什么把它作为控制准则？", "evaluation", "complex", "Directness 衡量回答是否具体、清晰且简洁地回应问题；它作为控制准则用于检验其他评测结果是否合理，而且通常与全面性和多样性相对，因此不期望同一方法赢得全部四项。", "graph_rag_2404_16130", 8, "control criterion"),
    ("holdout_graphrag_cost", "GraphRAG 在 Podcast 数据集上构建图索引使用什么窗口，耗时多久？", "cost", "simple", "实验使用 600-token 窗口建立图索引，在指定虚拟机和 GPT-4 Turbo 接口条件下耗时 281 分钟。", "graph_rag_2404_16130", 9, "took 281 minutes"),
    ("holdout_lightrag_domains", "LightRAG 从 UltraDomain 中选择了哪些领域进行实验？", "dataset", "simple", "选择了 Agriculture、CS、Legal 和 Mix 四个领域。", "light_rag_2410_05779", 5, "Agriculture, CS, Legal, and Mix"),
    ("holdout_react_errors", "ReAct 在 HotpotQA 错误分析中，推理错误和无信息搜索分别占多少？", "error_analysis", "simple", "ReAct 的失败样本中，推理错误占 47%，搜索结果为空或无用占 23%。", "react_2210_03629", 6, "Search result error"),
    ("holdout_reflexion_limit", "Reflexion 在 WebShop 实验中暴露了什么局限？", "limitation", "complex", "当任务陷入需要高度创造性行为才能跳出的局部最优时，Reflexion 难以改进；实验四次尝试后因无提升而终止，并且失败后的自我反思不够有帮助。", "reflexion_2303_11366", 14, "struggles to overcome local minima"),
    ("holdout_agent_memory_read", "LLM Agent Survey 总结的记忆读取通常考虑哪三个评分因素？", "memory", "simple", "通常考虑新近性、相关性和重要性三个因素，并通过权重平衡。", "agent_survey_2308_11432", 8, "recency, relevance, and importance"),
    ("holdout_agent_toolformer", "LLM Agent Survey 如何概括 ToolFormer 学习使用外部工具的方式？", "tool_use", "simple", "ToolFormer 使用自监督学习，并借助工具 API 的示例来学习何时以及如何调用外部工具。", "agent_survey_2308_11432", 15, "determine when and how to invoke external tools"),
]


def _find_anchor(text: str, anchor: str) -> int:
    """忽略 PDF 排版空白定位锚点，并返回原始文本字符位置。"""
    normalized_chars, original_positions = [], []
    for position, character in enumerate(text):
        if not character.isspace():
            normalized_chars.append(character.casefold())
            original_positions.append(position)
    normalized_anchor = re.sub(r"\s+", "", anchor.casefold())
    normalized_start = "".join(normalized_chars).find(normalized_anchor)
    return -1 if normalized_start < 0 else original_positions[normalized_start]


def build_holdout(papers_dir: Path, output: Path) -> Path:
    sources = json.loads((papers_dir / "corpus_sources.json").read_text(encoding="utf-8"))
    by_id = {item["document_id"]: item for item in sources["documents"]}
    parser, chunker = PyPDFPageParser(), FixedWindowChunker()
    pages_by_id, chunks_by_id = {}, {}
    for document_id, source in by_id.items():
        pages = parser.parse(papers_dir / source["filename"], document_id)
        pages_by_id[document_id] = {page.page_number: page for page in pages}
        chunks_by_id[document_id] = chunker.chunk(pages)
    cases = []
    for identity, question, category, difficulty, answer, document_id, page_number, anchor in SPECS:
        page = pages_by_id[document_id][page_number]
        start = _find_anchor(page.text, anchor)
        if start < 0:
            raise ValueError(f"保留集证据锚点未找到：{identity} / {anchor}")
        candidates = [chunk for chunk in chunks_by_id[document_id] if chunk.page_start == page_number and chunk.char_start <= start < chunk.char_end]
        if not candidates:
            raise ValueError(f"保留集证据未映射到 Chunk：{identity}")
        source = by_id[document_id]
        cases.append({"id": identity, "question": question, "language": "zh", "category": category, "difficulty": difficulty, "reference_answer": answer, "evidence": [{"document_id": document_id, "chunk_id": candidates[0].chunk_id, "page_start": page_number, "page_end": page_number, "quote": page.text[max(0, start - 180):min(len(page.text), start + len(anchor) + 300)].strip(), "source_path": f"data/papers/{source['filename']}", "relevance_grade": 3}]})
    payload = {"dataset_name": "PaperAgent 本地全文 RAG 独立保留金标准 v1", "dataset_version": "1.0.0-holdout", "description": "在术语表冻结后人工标注的 10 题保留集；证据页与开发集不重叠。", "corpus_version": sources["corpus_version"], "k_values": [1, 3, 5], "cases": cases}
    validated = RAGEvalDataset.model_validate(payload)
    output.parent.mkdir(parents=True, exist_ok=True); output.write_text(json.dumps(validated.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8"); return output


if __name__ == "__main__":
    print(build_holdout(Path("data/papers"), Path("eval_harness/datasets/rag_holdout_v1.json")))
