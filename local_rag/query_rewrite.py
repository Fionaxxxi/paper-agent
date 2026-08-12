"""显式、可审计且不调用 LLM 的科研中英术语查询扩展。"""

from __future__ import annotations


TERM_MAP = {
    "检索文档": "retrieved document",
    "使用": "use",
    "方式": "approach",
    "测试集": "test set",
    "分数": "score",
    "表示": "representation encode",
    "问题": "question query",
    "文本段": "passage",
    "相似度": "similarity",
    "提升幅度": "absolute improvement",
    "基线": "baseline",
    "四类": "four types",
    "分别判断": "decide definition",
    "移除": "remove no",
    "结果": "results",
    "传统": "conventional",
    "全局": "global",
    "源文档": "source documents",
    "处理链路": "pipeline",
    "双层检索": "dual-level retrieval",
    "低层": "low-level",
    "高层": "high-level",
    "增量更新": "incremental update",
    "知识库": "knowledge base",
    "核心工作模式": "reasoning acting interleaved",
    "绝对成功率": "absolute success rate",
    "短期记忆": "short-term memory",
    "长期记忆": "long-term memory",
    "总体准确率": "overall accuracy",
    "记忆写入": "memory writing",
    "记忆重复": "memory duplicated",
    "记忆溢出": "memory overflow",
    "复杂任务": "complex task",
    "初始计划": "initial plan",
    "外部反馈": "external feedback",
}


def expand_query(query: str) -> tuple[str, list[dict[str, str]]]:
    matches = []
    expansions = []
    for source, target in TERM_MAP.items():
        if source.casefold() in query.casefold():
            matches.append({"source": source, "target": target})
            expansions.append(target)
    rewritten = query if not expansions else f"{query} {' '.join(expansions)}"
    return rewritten, matches
