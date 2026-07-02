from typing import Any, Dict, List


EVAL_CASES: List[Dict[str, Any]] = [
    {
        "name": "citation_bibtex",
        "query": "把这几篇 RAG 论文生成 BibTeX",
        "conversation_id": "eval-citation",
        "pdf_path": None,
        "expected": {
            "task_type": "citation",
            "skill_used": "citation",
            "answer_contains": ["@article"],
        },
    },
    {
        "name": "reason_compare",
        "query": "比较这几篇 RAG 论文的方法差异",
        "conversation_id": "eval-compare",
        "pdf_path": None,
        "expected": {
            "task_type": "compare",
            "skill_used": "paper_compare",
            "answer_contains_any": ["对比", "比较", "差异", "区别", "方法"],
        },
    },
    {
        "name": "memory_first_turn",
        "query": "推荐几个 RAG 研究方向",
        "conversation_id": "eval-memory",
        "pdf_path": None,
        "expected": {
            "task_type": "recommend",
        },
    },
    {
        "name": "memory_second_turn",
        "query": "展开第二个方向",
        "conversation_id": "eval-memory",
        "pdf_path": None,
        "expected": {
            "history_count_gt": 0,
        },
    },
    {
        "name": "pdf_reading",
        "query": "总结这篇论文的研究问题、核心方法和主要贡献",
        "conversation_id": "eval-pdf",
        "pdf_path": "data/pdfs/test.pdf",
        "expected": {
            "task_type": "pdf_reading",
            "skill_used": "pdf_reading",
            "pdf_page_count_gt": 0,
        },
    },
]


CACHE_EVAL_CASE = {
    "name": "cache_hit",
    "query": "把这几篇 RAG 论文生成 BibTeX",
    "conversation_id": "eval-cache",
    "pdf_path": None,
    "expected": {
        "second_run_cache_hit": True,
    },
}