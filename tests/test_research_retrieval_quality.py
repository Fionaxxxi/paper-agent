from nodes.evaluate import rule_based_score
from nodes.generate import get_llm
from nodes.query_plan import query_plan_node
from nodes.query_rewrite import query_rewrite_node
from retrieval.research_query import filter_documents_by_year
from retrieval.strategy import select_retrieval_strategy


def _sft_state():
    return {
        "query": "梳理2023年以来SFT的代表论文、方法比较和研究空白",
        "rewritten_query": "梳理2023年以来SFT的代表论文、方法比较和研究空白",
        "task_level": "L3",
        "task_type": "summarize",
        "research_analysis": {
            "topic": "SFT (Supervised Fine-Tuning) 方法比较与研究空白",
            "requires_multiple_sources": True,
        },
    }


def test_l3_online_request_honors_multi_source_requirement(monkeypatch):
    from retrieval import strategy

    monkeypatch.setattr(strategy.settings, "RETRIEVAL_MODE", "arxiv")
    result = select_retrieval_strategy({**_sft_state(), "retrieval_scope": "online"})

    assert result["sources"] == ["arxiv", "openalex"]


def test_l3_plan_builds_english_provider_queries_for_sft():
    state = {
        **_sft_state(),
        "research_plan_validation": {"valid": True},
        "research_plan": {
            "tasks": [
                {"source": "arxiv", "objective": "筛选代表论文"},
                {"source": "openalex", "objective": "比较技术路线和优缺点"},
                {"source": "arxiv", "objective": "识别局限与研究空白"},
                {"source": "evidence_store", "objective": "综合"},
            ]
        },
    }

    result = query_plan_node(state)

    assert len(result["sub_queries"]) == 3
    assert all("监督" not in query and "研究空白" not in query for query in result["sub_queries"])
    assert all("SFT supervised fine-tuning" in query for query in result["sub_queries"])
    assert "open problems" in result["sub_queries"][2]


def test_sft_query_rewrite_exposes_normalized_english_topic():
    result = query_rewrite_node(_sft_state())

    assert result["rewritten_query"] == "SFT supervised fine-tuning large language models"


def test_year_constraint_removes_pre_2023_papers_but_keeps_unknown_year():
    documents = [
        {"title": "Old", "year": 2022},
        {"title": "Current", "year": 2024},
        {"title": "Unknown", "year": None},
    ]

    filtered, decision = filter_documents_by_year(documents, _sft_state()["query"])

    assert [item["title"] for item in filtered] == ["Current", "Unknown"]
    assert decision == {"enabled": True, "year_lower_bound": 2023, "removed_count": 1}


def test_relevant_sft_evidence_passes_without_chinese_exact_phrase_match():
    state = {
        **_sft_state(),
        "documents": [
            {"title": "Selective SFT", "content": "supervised fine-tuning improves diversity"},
            {"title": "Instruction Tuning", "content": "We study SFT data mixtures."},
            {"title": "Efficient Supervised Fine-Tuning", "content": "An LLM adaptation method."},
            {"title": "Unrelated Survey", "content": "Astronomy observations."},
        ],
    }

    assert rule_based_score(state) >= 0.7


def test_unrelated_results_remain_blocked_for_sft_research():
    state = {
        **_sft_state(),
        "documents": [
            {"title": "Galaxy Survey", "content": "Astronomy observations."},
            {"title": "Pathology Survey", "content": "Medical image classification."},
        ],
    }

    assert rule_based_score(state) < 0.7


def test_research_writer_has_bounded_output_budget(monkeypatch):
    from nodes import generate

    monkeypatch.setattr(generate.settings, "GENERATE_MAX_TOKENS", 1800)
    monkeypatch.setattr(generate.settings, "GENERATE_THINKING_BUDGET", 400)
    llm = get_llm()

    assert llm.max_tokens == 1800
    assert llm.extra_body == {"enable_thinking": True, "thinking_budget": 400}
