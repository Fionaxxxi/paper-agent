from local_rag.query_rewrite import expand_query


def test_query_expansion_preserves_original_and_adds_auditable_terms():
    rewritten, matches = expand_query("Reflexion 如何组织短期记忆与长期记忆？")
    assert rewritten.startswith("Reflexion 如何组织短期记忆与长期记忆？")
    assert "short-term memory" in rewritten and "long-term memory" in rewritten
    assert matches == [
        {"source": "短期记忆", "target": "short-term memory"},
        {"source": "长期记忆", "target": "long-term memory"},
    ]


def test_query_expansion_is_deterministic_and_leaves_unknown_query_unchanged():
    assert expand_query("未登记术语") == ("未登记术语", [])
    assert expand_query("初始计划") == expand_query("初始计划")
