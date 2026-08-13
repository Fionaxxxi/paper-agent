"""从已视觉核验且未被 v1 使用的 PDF 页面构建冻结验证集 v2。"""

from __future__ import annotations

import json
from pathlib import Path

from eval_harness.local_rag_dense_eval import _chunks


CASES = [
    ("v2_rag_fast_decoding","为什么 RAG-Sequence 的 Fast Decoding 比 Thorough Decoding 更高效？","Fast Decoding 假设未在某文档 beam 中生成的候选概率近似为零，因此候选集生成后不必再为缺失候选执行额外前向传播。","method","complex","rag_2005_11401:p4:c21"),
    ("v2_dpr_score_fusion","DPR 论文怎样组合 BM25 与 Dense Passage Retriever 的结果，融合权重如何确定？","先分别取得 BM25 和 DPR 的 top-2000 passage，合并候选后用 BM25(q,p)+λ·sim(q,p) 重排；λ=1.1，由开发集检索准确率选择。","method","complex","dpr_2004_04906:p5:c30"),
    ("v2_selfrag_adaptive_threshold","Self-RAG 在推理阶段如何通过阈值决定是否检索？","将 Retrieve=Yes token 在 Retrieve 选项中的归一化生成概率与阈值比较，超过阈值就触发检索。","method","simple","self_rag_2310_11511:p6:c37"),
    ("v2_graphrag_entity_matching","GraphRAG 原型怎样处理实体匹配和重复实体？","原型使用精确字符串匹配协调实体名称，也允许换成软匹配；重复实体通常会在后续摘要中聚到同一社区，因此系统对重复具有一定韧性。","method","complex","graph_rag_2404_16130:p5:c28"),
    ("v2_lightrag_evaluation_dimensions","LightRAG 使用 LLM 比较答案时采用哪四个评测维度？","四个维度是 Comprehensiveness、Diversity、Empowerment 和 Overall。","experiment","simple","light_rag_2410_05779:p6:c41"),
    ("v2_react_language_action","ReAct 为什么把语言加入 Agent 动作空间，语言动作会直接改变外部环境吗？","语言动作作为 thought/reasoning trace，用于整合当前上下文并支持后续推理或行动；它不会直接作用于外部环境，因此不会产生观察反馈。","method","complex","react_2210_03629:p3:c21"),
    ("v2_reflexion_long_memory","Reflexion 论文指出长期记忆在 ALFWorld 中主要帮助解决哪两类情况？","一是识别长轨迹中的早期错误并提出新动作或长期计划；二是需要检查过多表面或容器时，利用跨试验经验更彻底地搜索房间。","memory","complex","reflexion_2303_11366:p6:c32"),
    ("v2_agent_planning_no_feedback","Agent Survey 如何定义无反馈规划？","Agent 执行动作后不会收到能影响未来行为的反馈；单路径推理把任务分解成级联中间步骤，每一步只连接一个后续步骤。","planning","simple","agent_survey_2308_11432:p10:c51"),
]


def build_holdout_v2(papers_dir: Path, output_path: Path) -> Path:
    chunks,_,_=_chunks(papers_dir);by_id={chunk.chunk_id:chunk for chunk in chunks}
    filenames={item["document_id"]:item["filename"] for item in json.loads((papers_dir/"corpus_sources.json").read_text(encoding="utf-8"))["documents"]}
    cases=[]
    for identity,question,answer,category,difficulty,chunk_id in CASES:
        chunk=by_id[chunk_id]
        cases.append({"id":identity,"question":question,"language":"zh","category":category,"difficulty":difficulty,"reference_answer":answer,"evidence":[{"document_id":chunk.document_id,"chunk_id":chunk.chunk_id,"page_start":chunk.page_start,"page_end":chunk.page_end,"quote":chunk.text,"source_path":f"data/papers/{filenames[chunk.document_id]}","relevance_grade":3}]})
    dataset={"dataset_name":"PaperAgent 未见门控验证集 v2","dataset_version":"2.0.0","description":"8 篇论文各 1 题；证据页与开发集及 holdout v1 完全隔离，人工阅读 PDF 页面后标注。","corpus_version":"0.1.0","k_values":[1,3,5],"cases":cases}
    output_path.parent.mkdir(parents=True,exist_ok=True);output_path.write_text(json.dumps(dataset,ensure_ascii=False,indent=2),encoding="utf-8");return output_path


if __name__=="__main__": build_holdout_v2(Path("data/papers"),Path("eval_harness/datasets/rag_holdout_v2.json"))
