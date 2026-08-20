"""Human-readable purpose and result meanings for every unit-test function."""

from __future__ import annotations

from typing import TypedDict


class CaseDescription(TypedDict):
    purpose: str
    passed_meaning: str
    failed_meaning: str


def _description(
    purpose: str,
    passed_meaning: str,
    failed_meaning: str,
) -> CaseDescription:
    return {
        "purpose": purpose,
        "passed_meaning": passed_meaning,
        "failed_meaning": failed_meaning,
    }


TEST_CASE_CATALOG: dict[str, CaseDescription] = {
    "tests/test_research_analysis.py::test_rule_analyzer_separates_simple_comparison_and_deep_research": _description(
        "验证固定标注示例能分别识别 L1 简单检索、L2 比较和 L3 深度研究。",
        "典型复杂研究请求获得 Literature Review、评价维度和 L3 路由候选。",
        "任务分级错误会导致简单请求浪费 Token，或复杂请求无法进入 Research Agent。",
    ),
    "tests/test_research_analysis.py::test_simple_request_does_not_call_llm": _description(
        "验证明确的单主题论文检索只使用规则分析，不调用 Research Analyzer LLM。",
        "L1 快速路径保持零额外模型调用。",
        "简单检索会产生不必要 Token 和路由延迟。",
    ),
    "tests/test_research_analysis.py::test_complex_request_uses_structured_llm_analysis_and_builds_valid_plan": _description(
        "验证 L3 请求使用结构化 LLM 分析，并形成通过 Validator 的五任务受限计划。",
        "LLM 字段能传递给 Brief/Plan，且调用 Token 被准确记录。",
        "复杂意图分析与后续规划可能断裂，或额外模型成本漏记。",
    ),
    "tests/test_research_analysis.py::test_llm_analysis_failure_falls_back_to_bounded_rule_plan": _description(
        "验证 LLM 超时、JSON 错误或 Schema 失败时回退到规则分析和合法计划。",
        "Research Agent 不因结构化模型输出失败而中断，且明确记录 rule_fallback。",
        "复杂请求可能直接失败，或使用来源不明的残缺计划继续执行。",
    ),
    "tests/test_research_analysis.py::test_plan_validator_rejects_cycles_unknown_sources_and_dependencies": _description(
        "验证 Plan Validator 拒绝循环依赖、未知数据源和不存在的任务依赖。",
        "不合法计划不能进入未来 Executor。",
        "Scheduler 可能死循环、调用未授权来源或等待永远不会完成的任务。",
    ),
    "tests/test_research_analysis.py::test_brief_and_plan_respect_task_and_parallel_budgets": _description(
        "验证 Research Brief/Plan 严格限制最多五个任务和两个并行任务。",
        "复杂研究计划具备固定成本边界。",
        "Planner 可能生成过多任务或超出项目并发预算。",
    ),
    "tests/test_research_analysis.py::test_policy_gate_prevents_llm_downgrade_and_unknown_skills": _description(
        "验证 Policy Gate 阻止 LLM 将高置信度 L3 降级，并过滤不存在的主次 Skill。",
        "LLM 只补充语义分析，任务等级、检索要求和可执行 Skill 仍由代码控制。",
        "复杂研究任务可能被错误降级，或进入未注册/不安全的 Skill。",
    ),
    "tests/test_research_analysis.py::test_plan_validator_applies_current_brief_source_allowlist": _description(
        "验证 Plan Validator 除全局来源白名单外，还执行当前 Research Brief 的来源范围。",
        "计划只能使用本次任务明确允许的数据源。",
        "Planner 可能调用虽然系统存在、但本次研究未授权的数据源。",
    ),
    "tests/test_graph_checkpointer.py::test_official_sqlite_checkpointer_persists_state_across_graph_instances": _description(
        "验证官方 SqliteSaver 保存完整 LangGraph 状态，并能在重建 Graph 实例后按 thread_id 恢复。",
        "服务或进程重启后仍能读取已完成节点、答案和图结束位置。",
        "Checkpoint 可能只存在内存，无法支持后续 Research Graph 的中断恢复。",
    ),
    "tests/test_graph_checkpointer.py::test_sqlite_checkpointer_isolates_threads_and_supports_deletion": _description(
        "验证不同 thread_id 的图状态严格隔离，并支持删除指定线程全部 Checkpoint。",
        "两个会话分别保留 greeting/thanks 状态，删除一个不会影响另一个。",
        "图状态可能跨会话泄漏，或用户删除会话后仍残留执行轨迹。",
    ),
    "tests/test_graph_checkpointer.py::test_checkpointer_can_be_disabled_without_creating_a_database": _description(
        "验证关闭 Checkpoint 开关时不创建 SQLite 文件。",
        "测试、无状态部署或故障降级可以完全禁用图持久化。",
        "功能开关可能无效，导致禁用状态仍产生本地状态文件。",
    ),
    "tests/test_llm_wiki.py::test_verified_research_note_writes_markdown_evidence_and_index": _description(
        "验证通过 Verifier 的研究答案和论文证据能发布为 Markdown 笔记并进入 Wiki 索引。",
        "笔记包含结论、论文身份、来源、链接和验证状态，可由用户直接审阅。",
        "研究成果可能无法落盘，或 Wiki 丢失证据和质量审计信息。",
    ),
    "tests/test_llm_wiki.py::test_wiki_publish_gate_rejects_untrusted_or_disabled_results": _description(
        "验证 Wiki 拒绝关闭状态、不允许的任务、验证失败、无证据和证据不足结果。",
        "只有允许且可追溯的研究成果能进入长期 Wiki，不会污染知识记忆。",
        "普通问答或不可靠答案可能被自动固化为长期知识。",
    ),
    "tests/test_llm_wiki.py::test_republishing_same_trace_is_idempotent_in_index": _description(
        "验证相同 Trace 的研究笔记重新发布时更新内容而不重复增加索引项。",
        "修订结果可覆盖旧版本，Wiki 索引不会因重试或重复请求膨胀。",
        "重复发布可能留下冲突结论或大量重复链接。",
    ),
    "tests/test_llm_wiki.py::test_wiki_reader_sanitizes_note_identifier": _description(
        "验证 Wiki 读取接口清理 Note ID，不能使用路径穿越读取目录外文件。",
        "合法笔记可读取，包含路径字符的非法 ID 不会越过 notes 目录。",
        "用户提供的 Note ID 可能造成任意本地文件读取风险。",
    ),
    "tests/test_structured_memory.py::test_sqlite_memory_persists_messages_and_returns_recent_window": _description(
        "验证 SQLite 会话消息跨 Store 实例持久化，并只把最近窗口作为原文上下文。",
        "8 条消息完整落库，最近 3 条保持顺序，更早 5 条进入提取式摘要。",
        "服务重启后可能丢失记忆，或上下文窗口、摘要计数和消息顺序错误。",
    ),
    "tests/test_structured_memory.py::test_research_context_is_structured_deduplicated_and_conversation_scoped": _description(
        "验证用户偏好、活跃主题和论文以结构化字段保存、去重，并按 conversation_id 隔离。",
        "同一会话能合并 Research Context，不同会话不会读取彼此研究状态。",
        "研究上下文可能重复膨胀或跨会话泄漏，污染后续 Research Plan。",
    ),
    "tests/test_structured_memory.py::test_context_compression_respects_budget_and_keeps_each_memory_layer": _description(
        "验证上下文压缩遵守字符预算，同时保留研究状态、旧消息摘要和最近消息。",
        "有限上下文中三层信息均存在，长度不超过预算加固定分隔符。",
        "长会话可能无限增长，或压缩时完全丢失偏好、历史或最新问题。",
    ),
    "tests/test_structured_memory.py::test_checkpoint_round_trip_and_conversation_delete": _description(
        "验证研究状态 Checkpoint 可保存恢复，并在删除会话时级联清理消息和检查点。",
        "Research Plan 状态可恢复，用户删除会话后不会残留相关状态。",
        "中断研究任务无法恢复，或删除操作留下隐私和状态残留。",
    ),
    "tests/test_structured_memory.py::test_invalid_message_role_is_rejected": _description(
        "验证 MemoryStore 拒绝 user、assistant、system 之外的消息角色。",
        "非法角色不会进入会话上下文，消息契约保持稳定。",
        "未知角色可能污染 Prompt 格式或被错误解释成可信系统消息。",
    ),
    "tests/test_structured_memory.py::test_legacy_json_is_migrated_once_into_sqlite": _description(
        "验证已有 data/memory JSON 会话在首次读取时迁移到 SQLite，重复读取不会重复导入。",
        "用户旧会话仍可使用，迁移后消息数量和内容保持一致。",
        "切换存储后可能丢失旧会话，或每次读取重复插入历史消息。",
    ),
    "tests/test_structured_memory.py::test_service_injects_compressed_context_and_updates_research_memory": _description(
        "验证服务把结构化研究状态、旧摘要和最近消息注入 AgentState，并在回答后更新研究记忆。",
        "MemoryStore 已真正接入请求链路，API 元数据能报告被压缩的历史数量。",
        "存储模块虽能单独运行，但主服务可能仍使用旧上下文或没有保存研究状态。",
    ),
    "tests/test_answer_reflection.py::test_verifier_accepts_a_grounded_structured_answer": _description(
        "验证确定性 Verifier 能接受结构完整且明确关联论文证据的答案。",
        "合格答案不会触发额外 Reflection LLM 调用。",
        "Verifier 可能误报合格答案，造成不必要 Token、延迟或答案改写。",
    ),
    "tests/test_answer_reflection.py::test_verifier_only_requests_reflection_when_repair_evidence_exists": _description(
        "验证同样的答案缺陷只有在存在论文或 PDF 修复证据时才允许进入 Reflection。",
        "有证据的缺陷可修复，无证据时立即停止而不是要求模型猜测。",
        "系统可能基于空上下文修复答案并引入幻觉，或错过可修复问题。",
    ),
    "tests/test_answer_reflection.py::test_insufficient_evidence_answer_does_not_enter_reflection": _description(
        "验证已经明确披露证据不足的安全降级答案不会再次进入答案循环。",
        "检索预算耗尽后流程稳定停止，不会通过润色掩盖证据不足。",
        "低质量检索可能继续消耗 Token，或被模型改写成无依据结论。",
    ),
    "tests/test_answer_reflection.py::test_reflection_feature_flag_keeps_verification_but_disables_repair": _description(
        "验证关闭 ANSWER_REFLECTION_ENABLED 后仍保留质量检查，但不会进入 LLM 修复节点。",
        "项目可以独立关闭 Reflection 成本并保留 Verifier 观测与基线对照。",
        "功能开关可能无效，导致禁用状态仍产生额外模型调用。",
    ),
    "tests/test_answer_reflection.py::test_reflection_uses_one_tracked_llm_call_and_keeps_evidence_in_prompt": _description(
        "验证 Reflection 只使用现有证据修复答案，并将本次模型调用纳入 Token 统计。",
        "修复 Prompt 包含论文证据，调用次数和 30 个测试 Token 均被准确记录。",
        "Reflection 可能脱离证据生成，或其额外成本没有进入可观测指标。",
    ),
    "tests/test_answer_reflection.py::test_second_verification_restores_initial_answer_when_score_does_not_improve": _description(
        "验证修复答案没有提高验证分数时恢复初始答案并按无改善原因停止。",
        "Reflection 不会把原答案改得更差，也不会继续第三轮循环。",
        "无效修复可能覆盖较优答案或导致循环失去停止边界。",
    ),
    "tests/test_answer_reflection.py::test_graph_runs_answer_reflection_at_most_once": _description(
        "验证 LangGraph 的生成、验证、反思、再验证路径最多执行一次 Reflection。",
        "失败答案经过一次修复后进入 Metrics，图不存在无限答案循环。",
        "条件边或计数状态错误，可能跳过修复或重复调用大模型。",
    ),
    "tests/test_answer_reflection.py::test_metrics_records_answer_loop_quality_and_stop_outcome": _description(
        "验证 Metrics 暴露答案分数、Reflection 次数、原答案恢复状态和最终停止原因。",
        "Web、日志和后续评测能够解释答案循环的质量与停止结果。",
        "循环虽然执行但缺少可观测数据，无法统计修复收益、退化或预算停止。",
    ),
    "tests/test_tool_layer.py::test_router_exposes_an_auditable_route_decision": _description(
        "验证 Tool Router 不只返回工具名，还能给出可写入轨迹的能力、来源和工具路由决定。",
        "LangGraph 可以解释为什么选择某个工具，原生工具与 MCP 工具使用同一套路由记录。",
        "工具虽然能执行，但路由依据无法进入审计轨迹，出现问题时难以定位。",
    ),
    "tests/test_mcp_stdio_integration.py::test_real_stdio_mcp_server_is_registered_in_default_runtime": _description(
        "验证真实只读 MCP 工具已注册到默认运行时，并存在明确的 MCP 目录路由。",
        "配置选择 mcp_catalog 时 Router 能稳定解析到 paper.catalog.search.mcp。",
        "MCP 工具可能只能被单独测试，主运行时无法发现或选择它。",
    ),
    "tests/test_mcp_stdio_integration.py::test_main_retrieval_path_can_explicitly_route_to_mcp": _description(
        "验证主检索函数能够通过显式 mcp_catalog 来源调用真实 stdio MCP Server，并保存完整审计元数据。",
        "论文结果、路由能力、MCP 来源和 Server 身份均能传回 LangGraph 检索轨迹。",
        "MCP 与主工作流仍未连通，或执行记录丢失协议来源和 Server 身份。",
    ),
    "tests/test_zotero_mcp.py::test_zotero_client_uses_versioned_get_and_keeps_key_out_of_url": _description(
        "验证 Zotero 客户端固定使用 Web API v3 GET 请求，并从元数据、笔记和 PDF 子附件生成统一结果。",
        "API Key 只进入请求头，不出现在 URL 或返回数据中。",
        "若失败，认证信息可能泄漏，或个人文献证据无法规范化。",
    ),
    "tests/test_zotero_mcp.py::test_zotero_client_requires_explicit_library_and_rejects_unknown_type": _description(
        "验证缺少 Library ID 或使用未知库类型时立即拒绝执行。",
        "错误配置不会发送含糊或越界的 Zotero 请求。",
        "若失败，工具可能访问错误的个人库或群组库地址。",
    ),
    "tests/test_zotero_mcp.py::test_zotero_mcp_tool_is_registered_read_only": _description(
        "验证 Zotero MCP 已注册到默认 Registry、Router，并被标记为只读能力。",
        "主工作流只能通过 library.search/zotero 路由选择该工具。",
        "若失败，工具可能绕过统一权限层或无法被工作流发现。",
    ),
    "tests/test_zotero_mcp.py::test_zotero_schema_rejects_path_like_collection_key": _description(
        "验证 Collection Key 只能使用字母数字，拒绝路径式输入。",
        "用户参数不能改变 Zotero API 的固定资源边界。",
        "若失败，恶意参数可能构造非预期的 API 路径。",
    ),
    "tests/test_zotero_mcp.py::test_main_retrieval_path_routes_zotero_items_to_documents": _description(
        "验证 RETRIEVAL_MODE=zotero 时主检索链把 Zotero Item 转成统一文档并保留 MCP 审计轨迹。",
        "个人文献可以进入 Evidence Store 和 Research Writer，默认其他检索模式不变。",
        "若失败，Zotero 只能独立调用，无法参与 Research Agent 主流程。",
    ),
    "tests/test_zotero_mcp.py::test_zotero_failure_stays_empty_instead_of_using_public_fallback": _description(
        "验证 Zotero 配置或调用失败时返回空个人库结果和真实错误，不注入公共 fallback 论文。",
        "上层会明确进入证据不足路径，不把通用论文冒充用户收藏。",
        "若失败，个人库不可用可能被公共演示数据掩盖，导致来源误导。",
    ),
    "tests/test_prompt_contracts.py::test_external_documents_are_delimited_as_untrusted_evidence": _description(
        "验证论文、Zotero 笔记等外部文档被稳定边界标记为不可信证据。",
        "可疑文字保留供研究分析，但明确禁止覆盖角色、规则、密钥和工具权限。",
        "若失败，外部材料中的 Prompt Injection 可能被模型误认为系统指令。",
    ),
    "tests/test_prompt_contracts.py::test_research_writer_wraps_evidence_store_snippets": _description(
        "验证 Research Writer 的 Evidence Store snippet 也经过外部证据安全边界。",
        "稳定引用约束与 Prompt Injection 防护在深度研究路径同时生效。",
        "若失败，经过 Evidence Store 的恶意片段仍可能在最终写作阶段影响指令。",
    ),
    "tests/test_prompt_contracts.py::test_pdf_text_is_treated_as_untrusted_research_material": _description(
        "验证 PDF 提取文本只能作为研究材料，不能要求执行代码、调用工具或泄露配置。",
        "全文阅读路径与在线文献路径使用同一安全原则。",
        "若失败，论文正文中的恶意指令可能影响 PDF 分析模型。",
    ),
    "tests/test_prompt_contracts.py::test_llm_usage_records_prompt_version_for_future_ab_comparison": _description(
        "验证每次模型调用轨迹可记录实际 Prompt 版本。",
        "后续 zero-shot/few-shot A/B 可按版本比较准确率、Token 和延迟。",
        "若失败，Prompt 修改后无法准确归因能力和成本变化。",
    ),
    "tests/test_prompt_contracts.py::test_prompt_versions_cover_all_current_llm_prompt_families": _description(
        "验证当前分类、分析、Skill、Writer 和 Reflection Prompt 均有唯一版本号。",
        "新增 Prompt 家族必须显式进入版本注册表。",
        "若失败，部分模型调用可能继续使用不可追踪的 Prompt。",
    ),
    "tests/test_prompt_security_eval.py::test_prompt_security_dataset_is_frozen_and_covers_four_attack_paths": _description(
        "验证 Prompt 安全集冻结为四个唯一攻击案例并覆盖普通文档、PDF 和 Research Writer。",
        "对抗数据不会在看到模型结果后被随意修改。",
        "若失败，安全基线的版本或覆盖范围可能不可复现。",
    ),
    "tests/test_prompt_security_eval.py::test_every_adversarial_prompt_keeps_attack_inside_security_boundary": _description(
        "验证每个恶意片段完整保留在 UNTRUSTED_EVIDENCE 边界内。",
        "评测实际覆盖生产 Prompt 组装路径，而不是测试无关字符串。",
        "若失败，某类外部证据可能绕过统一安全边界。",
    ),
    "tests/test_prompt_security_eval.py::test_output_grader_rejects_canary_or_fake_evidence_and_requires_safe_content": _description(
        "验证判分器同时拒绝攻击标记、伪造 Evidence ID 和只拒答不回答研究问题的输出。",
        "通过结果必须既未服从攻击，又保留有用研究内容。",
        "若失败，空回答或攻击复述可能被错误算作安全成功。",
    ),
    "tests/test_prompt_security_eval.py::test_offline_mode_validates_contract_without_llm_or_tokens": _description(
        "验证默认对抗评测只检查 Prompt 契约，不调用真实模型。",
        "日常 CI 可零费用运行，在线测试必须由用户显式确认。",
        "若失败，普通测试可能意外产生模型费用。",
    ),
    "tests/test_research_analyzer_prompt_ab.py::test_few_shot_prompt_contains_boundary_examples_and_keeps_new_query_last": _description(
        "验证 few-shot 候选包含 L1/L2/L3 边界示例，并把待分析请求放在示例之后。",
        "模型先读取固定示例，再只处理最后的新请求。",
        "若失败，示例可能缺少关键边界或覆盖真实用户输入。",
    ),
    "tests/test_research_analyzer_prompt_ab.py::test_zero_shot_prompt_has_no_examples_and_unknown_variant_is_rejected": _description(
        "验证 zero-shot 保持紧凑，且未知 Prompt variant 不能静默回退。",
        "生产默认成本不变，配置错误会立即暴露。",
        "若失败，A/B 组可能混用 Prompt，导致结果不可解释。",
    ),
    "tests/test_research_analyzer_prompt_ab.py::test_analyzer_prompt_ab_dataset_is_frozen_and_has_six_l3_boundaries": _description(
        "验证 Analyzer A/B 数据集冻结为六个真正会进入 LLM 的 L3 边界案例。",
        "测试聚焦时间、趋势、空白、多维比较和多来源约束。",
        "若失败，A/B 可能测试生产中不会调用模型的简单路径。",
    ),
    "tests/test_research_analyzer_prompt_ab.py::test_analyzer_ab_grader_checks_objectives_dimensions_and_source_requirement": _description(
        "验证 A/B 判分同时检查等级、Skill、目标约束、评价维度、多来源和报告要求。",
        "结构化 JSON 能解析但遗漏研究约束时仍判失败。",
        "若失败，表面格式正确的低质量分析可能被错误晋升。",
    ),
    "tests/test_research_analyzer_prompt_ab.py::test_ab_promotion_requires_quality_gain_and_bounded_token_cost": _description(
        "验证 few-shot 只有质量提升至少10个百分点且 Token 增幅不超过250%时才允许晋升。",
        "准确率收益和成本共同进入选择门槛，默认离线模式保持零调用。",
        "若失败，高成本无收益 Prompt 可能被写入生产配置。",
    ),
    "tests/test_benchmark.py::test_baseline_and_candidate_cover_the_same_modules": _description(
        "确认旧基线与当前候选实现使用完全相同的能力模块，保证能力对比口径一致。",
        "两组结果都覆盖意图路由、查询规划、结果合并、重试路由、LLM 用量和工具执行六个模块。",
        "基线与候选的测试范围不同，能力提升数据不能直接比较。",
    ),
    "tests/test_benchmark.py::test_candidate_improves_deterministic_router_and_merger_accuracy": _description(
        "确认当前实现相对旧基线确实提升关键确定性能力的准确率。",
        "意图路由、结果去重、重试路由和 LLM 用量追踪准确率均高于基线。",
        "至少一个关键模块没有产生预期提升，需检查实现或基准案例。",
    ),
    "tests/test_benchmark.py::test_query_plan_benchmark_avoids_unnecessary_simple_queries": _description(
        "验证动态查询规划不会为简单问题创建多余检索词，同时保持规划准确。",
        "简单问题无多余查询、规划准确率为 100%，总规划查询数符合固定案例预期。",
        "简单问题可能浪费检索与 Token，或复杂度分类/查询数量发生回归。",
    ),
    "tests/test_benchmark.py::test_comparison_reports_baseline_candidate_and_delta": _description(
        "验证基准报告能同时给出基线值、候选值和差值。",
        "意图路由准确率正确记录为 40%、100% 和提升 60 个百分点。",
        "报告的版本对比计算或字段结构不正确。",
    ),
    "tests/test_benchmark.py::test_llm_usage_benchmark_tracks_success_failure_and_tokens": _description(
        "验证离线基准能准确统计成功/失败调用以及输入、输出和总 Token。",
        "三次调用、一次失败和 120/45/165 Token 均被准确记录。",
        "LLM 成本或失败率统计可能漏记、重复计算或口径错误。",
    ),
    "tests/test_benchmark.py::test_tool_execution_benchmark_measures_contracts_errors_and_recovery": _description(
        "验证离线基准能够量化统一 Tool 层的协议、错误和恢复能力。",
        "候选实现达到 100%，能够拦截权限、输入和输出错误、结构化四类失败并恢复一次临时错误。",
        "Tool 层能力提升没有可重复数据支持，或错误门控、重试行为出现回归。",
    ),
    "tests/test_benchmark.py::test_benchmark_report_can_be_written_as_utf8_json": _description(
        "验证完整能力基准报告可以用 UTF-8 JSON 保存并重新读取。",
        "报告文件可读取，版本、运行模式和案例数等关键字段保持正确。",
        "基准报告无法可靠落盘，或中文/结构化字段可能损坏。",
    ),
    "tests/test_benchmark.py::test_unknown_profile_is_rejected": _description(
        "验证基准工具拒绝不存在的运行配置名称。",
        "传入未知 profile 时明确抛出 ValueError，而不是静默使用错误配置。",
        "错误配置可能被接受，导致产生来源不明或不可比较的基准数据。",
    ),
    "tests/test_graph_integration.py::test_standard_query_runs_the_agentic_rag_path": _description(
        "验证普通研究问题按完整 Agentic RAG 节点顺序执行。",
        "流程依次经过改写、规划、检索、评估、推理、生成和指标节点，并返回答案与子查询。",
        "图路由顺序、节点连接或状态传递出现回归。",
    ),
    "tests/test_graph_integration.py::test_pdf_query_skips_query_planning_and_retrieval": _description(
        "验证已有 PDF 的请求不会重复进行外部查询规划和检索。",
        "PDF 请求只经过改写、推理、生成和指标节点，避免不必要检索。",
        "PDF 流程误入外部检索，增加延迟、Token 或引入无关资料。",
    ),
    "tests/test_graph_integration.py::test_smalltalk_ends_before_all_rag_and_llm_nodes": _description(
        "验证问候类输入在进入 RAG 与 LLM 节点前本地结束。",
        "没有调用任何后续节点，答案由本地生成，工具与 Token 用量为零并标记短路。",
        "简单问候可能触发完整 Agent 流程，造成不必要 Token 和延迟。",
    ),
    "tests/test_intent_router.py::test_classifies_exact_greetings_without_an_llm": _description(
        "验证不同语言和格式的纯问候可由本地规则识别。",
        "当前参数场景被分类为 greeting，不需要调用 LLM。",
        "问候可能被误送入研究流程，浪费 Token；或被分类为错误意图。",
    ),
    "tests/test_intent_router.py::test_classifies_thanks_without_an_llm": _description(
        "验证中英文感谢表达可由本地规则识别。",
        "当前参数场景被分类为 thanks，不需要调用 LLM。",
        "感谢语可能触发完整研究流程或得到不合适的回复。",
    ),
    "tests/test_intent_router.py::test_classifies_identity_questions_without_an_llm": _description(
        "验证“你是谁/能做什么”等身份能力问题可本地识别。",
        "当前参数场景被分类为 identity，不需要调用 LLM。",
        "身份问题可能错误触发检索或无法返回预设能力说明。",
    ),
    "tests/test_intent_router.py::test_does_not_short_circuit_research_or_pdf_requests": _description(
        "防止含问候词的真实研究请求或 PDF 请求被错误当成闲聊短路。",
        "当前参数场景仍被分类为 research，会继续执行所需研究流程。",
        "真实论文检索、比较或 PDF 分析请求可能被提前终止。",
    ),
    "tests/test_intent_router.py::test_normalize_message_only_removes_superficial_variations": _description(
        "验证意图匹配前只清理空格、大小写和末尾标点等表面差异。",
        "带空格、大小写和标点的 HELLO 被稳定归一化为 hello。",
        "归一化规则过弱会漏识别，过强则可能改变用户真实语义。",
    ),
    "tests/test_intent_router.py::test_smalltalk_result_is_local_and_preserves_existing_state_metadata": _description(
        "验证本地闲聊响应不会破坏已有状态和请求元数据。",
        "本地答案、空文档、零 Token、原 conversation_id 和短路标记同时保留。",
        "闲聊优化可能覆盖上下文、误报用量或遗失会话标识。",
    ),
    "tests/test_llm_usage.py::test_extracts_langchain_usage_metadata": _description(
        "验证能读取 LangChain 标准 usage_metadata Token 字段。",
        "输入、输出和总 Token 被按 120/30/150 提取，并标记数据可用。",
        "LangChain 模型调用的 Token 可能无法计费或被错误统计。",
    ),
    "tests/test_llm_usage.py::test_extracts_openai_compatible_response_metadata": _description(
        "验证能读取 OpenAI 兼容响应中的 token_usage 字段。",
        "prompt、completion 和 total Token 被映射为统一内部格式。",
        "兼容 OpenAI 的模型响应可能出现用量漏记。",
    ),
    "tests/test_llm_usage.py::test_missing_usage_is_explicit_instead_of_estimated": _description(
        "验证模型未返回 Token 数据时系统明确标记缺失而不伪造估算值。",
        "所有 Token 为零且 token_usage_available 为 false。",
        "缺失数据可能被误当成真实零用量或产生不可信估算。",
    ),
    "tests/test_llm_usage.py::test_successful_invocation_records_model_node_tokens_and_latency": _description(
        "验证成功 LLM 调用会记录节点、模型、Token、成功状态和延迟。",
        "响应原样返回，并生成完整且非负延迟的 generate 节点用量记录。",
        "成功调用的成本、归属节点或性能数据可能缺失。",
    ),
    "tests/test_llm_usage.py::test_failed_invocation_preserves_call_and_latency_record": _description(
        "验证 LLM 调用失败时仍保留失败类型和耗时记录。",
        "TimeoutError 被包装保留，失败标记、零 Token 和非负延迟均存在。",
        "失败调用可能从指标中消失，导致稳定性与成本分析失真。",
    ),
    "tests/test_llm_usage.py::test_multiple_node_records_are_aggregated_without_double_counting": _description(
        "验证多个节点的 LLM 用量可以累加且不会重复计数。",
        "两次调用累计为输入 120、输出 45、总计 165 Token，失败数为零。",
        "跨节点汇总可能少算或重复计算 Token 与调用次数。",
    ),
    "tests/test_llm_usage.py::test_metrics_groups_usage_by_node_and_reports_totals": _description(
        "验证指标节点既能按节点分组，又能提供全流程总量与缺失用量统计。",
        "reason/generate 分组、失败数、总 Token、缺失次数和总延迟均正确。",
        "监控报告无法定位高成本或失败节点，或总量与明细不一致。",
    ),
    "tests/test_llm_usage_nodes.py::test_reason_node_records_llm_usage": _description(
        "验证推理节点启用 LLM 时会写入统一用量记录。",
        "任务类型解析正确，并记录一次 reason 调用和 13 Token。",
        "推理节点的模型调用可能未计入成本和性能指标。",
    ),
    "tests/test_llm_usage_nodes.py::test_evaluate_node_records_usage_only_when_llm_is_enabled": _description(
        "验证检索评估节点启用 LLM 时记录评分与用量。",
        "返回 0.8 评分，并记录一次 evaluate 调用和 31 Token。",
        "LLM 评估产生的成本可能漏记，或评分结果处理错误。",
    ),
    "tests/test_llm_usage_nodes.py::test_generate_node_records_usage": _description(
        "验证答案生成节点记录实际生成结果和模型用量。",
        "返回 grounded answer，并记录一次 generate 调用和 120 Token。",
        "最终生成成本、调用次数或答案传递可能出现回归。",
    ),
    "tests/test_llm_usage_nodes.py::test_rule_based_evaluate_does_not_create_an_llm_call": _description(
        "验证关闭 LLM 评估时只使用规则评分且不创建虚假调用记录。",
        "结果包含有效规则评分，但没有 llm_call_count。",
        "关闭模型后仍可能调用 LLM、误报用量或无法评分。",
    ),
    "tests/test_query_plan.py::test_deduplicate_queries_preserves_order_and_ignores_case": _description(
        "验证查询去重忽略大小写和首尾空格，同时保留首次出现顺序。",
        "重复 Graph RAG/Methods 被合并，输出顺序保持稳定。",
        "可能产生重复检索、顺序变化或错误删除有效查询。",
    ),
    "tests/test_query_plan.py::test_build_rule_based_sub_queries_for_each_task_type": _description(
        "验证不同任务类型生成对应的规则子查询集合。",
        "当前任务场景保留原查询，并追加预期的比较、总结、推荐或引用检索后缀。",
        "任务类型与检索策略不匹配，可能漏找关键论文维度或增加无效查询。",
    ),
    "tests/test_query_plan.py::test_build_rule_based_sub_queries_falls_back_to_original_query": _description(
        "验证改写查询为空时使用原始用户问题兜底。",
        "仍能得到 agentic rag 单查询，不会返回空规划。",
        "查询改写异常可能导致完全不检索。",
    ),
    "tests/test_query_plan.py::test_classify_query_complexity_without_an_llm": _description(
        "验证本地复杂度规则可区分简单、复杂和不适用任务。",
        "当前参数场景得到预期复杂度，并提供非空判断原因。",
        "简单问题可能多检索浪费资源，复杂问题可能检索不足，或 PDF 被误规划。",
    ),
    "tests/test_query_plan.py::test_query_plan_node_skips_pdf_reading_tasks": _description(
        "验证 PDF 阅读任务完全跳过外部检索规划。",
        "子查询为空、规划关闭，复杂度和原因字段明确标记不适用。",
        "PDF 分析可能错误触发搜索，增加延迟并混入外部内容。",
    ),
    "tests/test_query_plan.py::test_query_plan_node_preserves_and_extends_paper_metadata": _description(
        "验证查询规划在扩展论文元数据时保留已有请求信息。",
        "request_id 保留，并新增一致的子查询、数量、复杂度和启用原因。",
        "规划节点可能丢失追踪信息或写入相互矛盾的状态。",
    ),
    "tests/test_result_merger.py::test_normalize_text_handles_none_whitespace_and_case": _description(
        "验证文档去重使用的文本归一化能处理空值、空格和大小写。",
        "None 变为空串，Graph RAG 被稳定归一化为 graph rag。",
        "同一文档可能因格式差异无法去重，或空值引发异常。",
    ),
    "tests/test_result_merger.py::test_build_document_key_uses_stable_priority": _description(
        "验证文档唯一键按 DOI、entry_id、PDF URL、标题的稳定优先级选择。",
        "跨源 DOI 优先，每种后备标识生成预期键，无标识文档返回空键。",
        "同一论文可能生成不稳定键，导致重复或误合并。",
    ),
    "tests/test_result_merger.py::test_merge_documents_deduplicates_across_groups_and_preserves_priority": _description(
        "验证多查询结果跨组去重，并保留首次出现的高优先级版本。",
        "重复 entry_id 只保留 first，第二篇独立论文仍保留。",
        "合并结果可能含重复论文或被后到的低优先级数据覆盖。",
    ),
    "tests/test_result_merger.py::test_merge_documents_deduplicates_cross_source_records_by_doi": _description(
        "验证 arXiv 与 OpenAlex 使用不同平台 ID 时仍能通过 DOI 识别同一论文。",
        "大小写和 DOI URL 表示不同的两条记录只保留优先来源版本。",
        "多源检索可能重复展示同一论文并浪费上下文 Token。",
    ),
    "tests/test_result_merger.py::test_merge_documents_deduplicates_cross_source_title_when_doi_is_missing": _description(
        "验证没有 DOI 的同一预印本可通过归一化标题跨来源去重。",
        "不同平台 ID、标题大小写和空格不同的记录只保留 arXiv 优先版本。",
        "无 DOI 预印本可能因平台 ID 不同而在多源结果中重复出现。",
    ),
    "tests/test_result_merger.py::test_merge_documents_keeps_documents_without_a_deduplication_key": _description(
        "验证缺少稳定标识的匿名结果不会被错误互相合并。",
        "两条无去重键文档均被保留。",
        "不同匿名内容可能被误删，造成检索信息丢失。",
    ),
    "tests/test_result_merger.py::test_merge_documents_honors_max_documents": _description(
        "验证合并结果遵守最大文档数量限制。",
        "五篇输入在上限为三时只返回前三篇。",
        "上下文可能超过设定限制，增加 Token、延迟或截断风险。",
    ),
    "tests/test_result_merger.py::test_merge_documents_with_stats_reports_counts": _description(
        "验证带统计的合并能准确报告原始数、合并数和去重数。",
        "四条原始结果合并为三篇，准确报告去除一条重复。",
        "去重效果指标可能与实际文档列表不一致。",
    ),
    "tests/test_retrieve_planning.py::test_single_planned_query_uses_single_query_retrieval": _description(
        "验证只有一个规划查询时走低成本单查询检索路径。",
        "只调用 single retrieval，agentic_rag_enabled 为 false，并保留缓存来源。",
        "简单问题可能误用多查询检索，造成额外请求与 Token 消耗。",
    ),
    "tests/test_retrieve_planning.py::test_multiple_planned_queries_use_multi_query_retrieval": _description(
        "验证多个规划查询时启用多查询检索。",
        "完整查询列表传入 multi retrieval，并标记 Agentic RAG 已启用。",
        "复杂问题可能只检索一个角度，降低论文覆盖度。",
    ),
    "tests/test_test_report.py::test_parse_junit_xml_normalizes_status_duration_and_message": _description(
        "验证测试报告采集器能把 JUnit XML 转成统一明细记录。",
        "通过、失败、错误、跳过状态及文件、耗时、消息和详情均正确解析。",
        "Excel/CSV 报告可能漏掉测试、错误状态或失败原因。",
    ),
    "tests/test_test_report.py::test_summarize_calculates_counts_rate_and_duration": _description(
        "验证测试报告总览的数量、通过率、耗时和退出码计算。",
        "四个示例用例被汇总为 2 通过、1 失败、1 跳过、50% 通过率和 0.875 秒。",
        "测试总览指标可能与明细不一致，导致质量判断错误。",
    ),
    "tests/test_test_catalog.py::test_catalog_exactly_covers_all_test_functions": _description(
        "强制每个测试函数都登记作用、通过含义和失败含义，并清理失效记录。",
        "测试源码中的函数集合与说明目录完全一致，且三个说明字段均非空。",
        "存在未说明的新测试、已删除测试的遗留记录，或说明字段不完整。",
    ),
    "tests/test_tool_layer.py::test_registry_registers_discovers_and_filters_tools": _description(
        "验证 Tool Registry 可以注册、按名称发现并按能力筛选工具。",
        "工具注册顺序稳定，paper 等能力可以通过统一入口发现，不依赖业务节点直接导入。",
        "后续多数据源或 MCP 工具可能无法可靠注册、发现或路由。",
    ),
    "tests/test_tool_layer.py::test_registry_rejects_duplicate_tool_names": _description(
        "验证 Registry 拒绝相同稳定名称的重复工具。",
        "重复注册会明确报错，避免工具实现被静默覆盖。",
        "同名工具可能覆盖旧实现，导致实际执行版本不可追踪。",
    ),
    "tests/test_tool_layer.py::test_executor_returns_structured_error_for_unknown_tool": _description(
        "验证执行不存在的工具时返回标准化错误而不是抛出未处理异常。",
        "结果包含 TOOL_NOT_FOUND、零执行次数和可观测延迟。",
        "错误路由可能让 LangGraph 整体崩溃或产生无法分类的失败。",
    ),
    "tests/test_tool_layer.py::test_executor_rejects_invalid_input_without_invoking_tool": _description(
        "验证 Tool Executor 在执行前使用 Pydantic 校验输入参数。",
        "非法参数被 INVALID_INPUT 拦截，底层工具完全没有执行。",
        "错误参数可能进入外部 API，浪费调用额度或触发不可控行为。",
    ),
    "tests/test_tool_layer.py::test_executor_blocks_non_read_only_tool_before_invocation": _description(
        "验证默认 ToolPolicy 在调用前拒绝非只读工具。",
        "写工具返回 PERMISSION_DENIED、执行次数为零，底层函数没有运行。",
        "风险等级可能只被记录而未执行，导致未授权写操作进入外部系统。",
    ),
    "tests/test_tool_layer.py::test_executor_validates_output_and_records_execution_metadata": _description(
        "验证成功工具调用会校验输出并记录版本、来源、能力、风险和延迟。",
        "标准数据、工具版本、一次执行和只读风险元数据全部准确返回。",
        "下游可能收到不可信结构，或无法审计工具版本、来源和成本。",
    ),
    "tests/test_tool_layer.py::test_executor_retries_retryable_failure_then_returns_success": _description(
        "验证临时执行错误可以按照有限 RetryPolicy 重试。",
        "第一次连接错误后只重试一次并成功，attempt_count 准确记录为 2。",
        "临时错误可能无法恢复，或工具发生无上限重复调用。",
    ),
    "tests/test_tool_layer.py::test_executor_returns_structured_rate_limit_after_finite_retries": _description(
        "验证数据源限流经过有限次数重试后返回独立标准错误码。",
        "执行两次后停止并返回 RATE_LIMITED，不会无限消耗 API 额度。",
        "429 可能被误记为普通异常、无法触发正确恢复，或产生无限重试。",
    ),
    "tests/test_tool_layer.py::test_executor_returns_timeout_after_bounded_wait": _description(
        "验证工具超过配置时间后返回结构化超时错误。",
        "执行在有限等待后返回 TIMEOUT，并准确记录一次尝试。",
        "外部工具可能无限阻塞请求，或超时无法被失败路由识别。",
    ),
    "tests/test_tool_layer.py::test_executor_rejects_output_that_breaks_tool_contract": _description(
        "验证工具返回值不符合输出 Schema 时被拒绝。",
        "缺失 doubled 字段的输出返回 INVALID_OUTPUT，不会传给下游节点。",
        "外部 API 或 MCP 结构变化可能静默污染 AgentState。",
    ),
    "tests/test_tool_layer.py::test_router_resolves_registered_capability_and_source": _description(
        "验证 Tool Router 根据能力与数据源选择稳定工具名称。",
        "arXiv 路由正确，未注册的 OpenAlex 路由明确失败。",
        "数据源选择可能错误或在无实现时静默调用其他工具。",
    ),
    "tests/test_tool_layer.py::test_arxiv_adapter_preserves_native_search_behavior": _description(
        "验证 arXiv Adapter 保留现有查询词、数量和论文字段。",
        "适配器把相同参数传给原生函数，并完整返回论文标识。",
        "工具层改造可能改变原有 arXiv 行为或丢失论文字段。",
    ),
    "tests/test_tool_layer.py::test_metrics_reports_tool_execution_success_failure_and_latency": _description(
        "验证 Metrics 汇总每次工具调用的成功、失败、耗时和错误明细。",
        "两次调用准确统计为一成功、一失败、总耗时 2 秒，并保留 TIMEOUT。",
        "工具观测数据可能漏记或汇总错误，无法支持多数据源和 MCP 评测。",
    ),
    "tests/test_benchmark.py::test_multi_source_benchmark_measures_coverage_deduplication_and_recovery": _description(
        "验证离线 Benchmark 对比单源基线与多源候选的覆盖、去重和故障恢复。",
        "候选三类场景达到 100%，调用两个来源、无残留重复并恢复一次局部失败。",
        "多源能力可能只有功能测试，没有可比较的质量与可靠性提升数据。",
    ),
    "tests/test_retrieve_tool_integration.py::test_cache_miss_uses_tool_runtime_and_records_execution": _description(
        "验证缓存未命中时 Retrieve Node 通过 Router 和 Executor 调用 arXiv。",
        "统一工具名称、查询参数、论文结果、缓存写入和执行指标全部正确。",
        "检索节点可能仍直接依赖 arXiv，或工具结果无法进入现有缓存和文档流程。",
    ),
    "tests/test_retrieve_tool_integration.py::test_tool_failure_uses_existing_fallback_and_keeps_error_metadata": _description(
        "验证统一工具执行失败后沿用现有 fallback，并保留失败原因。",
        "超时不会使图崩溃，静态兜底文档可用且 TIMEOUT 元数据未丢失。",
        "外部工具失败可能中断流程，或降级后无法定位原始错误。",
    ),
    "tests/test_openalex_tool.py::test_reconstruct_abstract_orders_openalex_inverted_positions": _description(
        "验证 OpenAlex 倒排摘要能够按照词位还原为可读文本。",
        "乱序词典被恢复为正确句子，缺失摘要安全返回空串。",
        "论文摘要可能词序错乱，污染相关性评分和最终答案。",
    ),
    "tests/test_openalex_tool.py::test_normalize_openalex_work_maps_stable_paper_fields": _description(
        "验证 OpenAlex Work 的作者、摘要、链接、DOI 和引用数映射到统一论文结构。",
        "嵌套 API 字段被完整转换，来源明确标记为 openalex。",
        "多数据源字段可能丢失或以不一致结构进入 LangGraph。",
    ),
    "tests/test_openalex_tool.py::test_openalex_client_sends_search_limits_identity_and_optional_key": _description(
        "验证 OpenAlex Client 使用官方 search 参数、数量限制、身份头和可选凭据。",
        "请求 URL、per-page、API key、mailto、超时和 User-Agent 均符合配置。",
        "请求可能使用过期参数、泄漏配置或绕过调用预算和超时。",
    ),
    "tests/test_openalex_tool.py::test_openalex_client_maps_rate_limit_for_executor_recovery": _description(
        "验证限流等 HTTP 错误不会被伪装成正常空结果。",
        "429 被转换成 ToolRateLimitError，交给 Tool Executor 统一重试和记录。",
        "网络失败可能被误判为无论文，导致无法观测、重试或定位问题。",
    ),
    "tests/test_openalex_tool.py::test_openalex_adapter_delegates_to_injected_client": _description(
        "验证 OpenAlex Adapter 保持统一 Tool 输入并调用可替换 Client。",
        "查询词和最大数量不变，输出满足统一论文来源约定。",
        "Adapter 可能篡改参数、耦合网络实现或返回非标准结构。",
    ),
    "tests/test_openalex_tool.py::test_default_runtime_registers_and_routes_openalex_tool": _description(
        "验证默认 Tool Runtime 同时注册并可路由 OpenAlex 原生工具。",
        "paper.search/openalex 稳定解析到 paper.search.openalex。",
        "代码虽有 Adapter，但实际 LangGraph 运行时可能无法发现或调用。",
    ),
    "tests/test_openalex_tool.py::test_cache_keys_are_isolated_by_paper_source": _description(
        "验证同一查询在 arXiv 与 OpenAlex 使用独立缓存键。",
        "来源不同得到不同键，同来源大小写和空格归一化后键保持一致。",
        "不同数据源的论文可能互相污染缓存并产生虚假命中。",
    ),
    "tests/test_multi_source_retrieval.py::test_multi_source_retrieval_calls_both_tools_and_deduplicates_by_doi": _description(
        "验证 multi 模式调用 arXiv 与 OpenAlex，并按 DOI 合并重复论文。",
        "两个 Tool 都执行，三条原始记录合并为两篇并记录一次去重。",
        "多源模式可能只调用一个来源、保留重复论文或统计不一致。",
    ),
    "tests/test_retrieval_online_eval.py::test_retrieval_dataset_loads_versioned_twenty_case_gold_standard": _description(
        "验证在线检索评测集具有固定版本、20 个唯一问题、统一 K 值和非空金标准论文。",
        "评测输入可追溯且结构完整，不会因重复问题或缺少相关论文而污染指标。",
        "评测集版本、规模或标注结构发生意外变化，历史结果将失去可比性。",
    ),
    "tests/test_retrieval_online_eval.py::test_retrieval_dataset_rejects_duplicate_case_ids": _description(
        "验证评测集拒绝重复 case id，避免同一问题被重复计分。",
        "重复标识会在加载阶段被明确拒绝。",
        "重复问题可能被静默纳入平均值，造成检索质量指标偏差。",
    ),
    "tests/test_retrieval_online_eval.py::test_paper_identity_normalizes_doi_arxiv_id_and_title": _description(
        "验证 DOI、arXiv ID 和标题能被归一化为稳定的论文身份键。",
        "不同 URL、大小写和标点形式仍能识别为同一论文。",
        "同一论文可能无法匹配金标准或无法跨来源去重。",
    ),
    "tests/test_retrieval_online_eval.py::test_gold_match_rejects_stable_identity_with_contradictory_title": _description(
        "验证 DOI/arXiv ID 相同但标题严重冲突的来源记录不会被金标准误判为相关论文。",
        "异常 OpenAlex 标题即使复用了金标准 DOI，也不会虚增 Recall、MRR 或 nDCG。",
        "来源元数据污染可能制造虚假能力提升，使重排技术选型结论失真。",
    ),
    "tests/test_retrieval_online_eval.py::test_ranking_metrics_calculate_recall_precision_mrr_ndcg_and_dimensions": _description(
        "用手工可验证的排名检查 Recall、Precision、MRR、nDCG 和维度覆盖率公式。",
        "相关论文位于第 2 名时，各项指标与预先计算值完全一致。",
        "至少一个核心检索指标计算错误，在线来源对比结论不可信。",
    ),
    "tests/test_retrieval_online_eval.py::test_duplicate_rate_handles_zero_and_merged_counts": _description(
        "验证空结果和存在重复结果时的重复率计算边界。",
        "空结果返回 0%，4 条合并为 3 条时返回 25%。",
        "重复率可能除零或错误反映多来源结果冗余。",
    ),
    "tests/test_retrieval_online_eval.py::test_multi_profile_deduplicates_and_records_partial_provider_failure": _description(
        "验证多来源评测在一个来源失败时仍合并成功来源，并保留失败原因。",
        "结果标记为部分成功，相关论文仍被命中，TIMEOUT 明细可追踪。",
        "单来源故障可能拖垮整个评测，或错误被隐藏为正常空结果。",
    ),
    "tests/test_retrieval_online_eval.py::test_successful_zero_result_is_empty_instead_of_failed": _description(
        "验证来源正常响应但没有论文时标记为 empty，而不是网络或执行失败。",
        "空结果与工具故障采用不同状态，且不会产生虚假的来源错误。",
        "失败率会混入正常零结果，导致可靠性与检索覆盖问题无法区分。",
    ),
    "tests/test_retrieval_online_eval.py::test_online_benchmark_reuses_provider_results_across_profiles": _description(
        "验证同一问题的原始来源响应会在 arXiv、OpenAlex 和 multi 配置间复用。",
        "每个来源只调用一次，三种配置基于相同快照比较，避免浪费 API 配额。",
        "同一轮对比可能重复联网，增加耗时、限流风险并破坏公平性。",
    ),
    "tests/test_retrieval_online_eval.py::test_missing_openalex_key_is_explicitly_skipped_without_network": _description(
        "验证缺少 OpenAlex API Key 时明确跳过该来源且不发起网络请求。",
        "报告记录 MISSING_API_KEY，实际 API 调用数保持为零。",
        "无凭据运行可能消耗匿名额度，或把配置缺失误报为检索质量差。",
    ),
    "tests/test_retrieval_online_eval.py::test_arxiv_pacing_waits_only_for_remaining_interval": _description(
        "验证在线评测在连续 arXiv 请求之间只等待尚未满足的全局间隔，并能识别 HTTP 429。",
        "已过去 2.5 秒时只等待剩余 3.5 秒，OpenAlex 不受该节流影响，429 可触发恢复。",
        "评测可能请求过快触发限流，或不必要地拖慢其他论文来源。",
    ),
    "tests/test_retrieval_online_eval.py::test_online_report_writes_json_summary_case_and_paper_tables": _description(
        "验证在线评测可同时输出机器可读 JSON、快照清单及总览、逐题、论文明细 CSV。",
        "报告文件和快照清单均成功生成，且清单保存稳定的快照身份。",
        "评测结果无法沉淀为可审计数据，Excel 和历史对比也无法稳定生成。",
    ),
    "tests/test_retrieval_online_eval.py::test_snapshot_id_is_path_safe_and_uses_isolated_directory": _description(
        "验证在线评测快照 ID 只能使用安全字符，并映射到独立快照目录。",
        "合法 ID 获得独立目录，路径穿越、嵌套路径、空值和非约定字符均被拒绝。",
        "快照名称可能逃逸评测目录、覆盖其他文件，或让两次来源响应混入同一实验。",
    ),
    "tests/test_retrieval_online_eval.py::test_existing_snapshot_requires_explicit_resume": _description(
        "验证已有在线评测快照默认不可覆盖，只有显式续跑才能复用其成功响应。",
        "普通运行遇到已有快照立即失败，resume 模式准确返回原快照目录。",
        "第二次实验可能静默覆盖第一份证据，导致跨快照结论无法审计和复现。",
    ),
    "tests/test_retrieval_snapshot_compare.py::test_snapshot_comparison_passes_stable_complete_non_regressing_candidate": _description(
        "验证两份完整快照在质量不回归且隔离集合稳定时可以通过晋升门槛。",
        "质量提升、逐题无回归、隔离集合完全一致，比较器明确返回 promotion_ready。",
        "稳定候选可能因比较口径错误被拒绝，阻碍经过复现验证的能力晋升。",
    ),
    "tests/test_retrieval_snapshot_compare.py::test_snapshot_comparison_blocks_quality_or_quarantine_instability": _description(
        "验证跨快照出现逐题质量下降或隔离集合漂移时阻止默认启用候选策略。",
        "比较器同时报告质量回归与隔离不稳定，并输出需要人工复核的新增和移除记录。",
        "只看平均指标可能掩盖逐题退化或误伤漂移，让不稳定元数据策略进入默认流程。",
    ),
    "tests/test_retrieval_online_eval.py::test_arxiv_network_failure_propagates_to_tool_executor": _description(
        "验证 arXiv 网络异常会传递给 Tool Executor，而不是被伪装成零篇论文。",
        "连接失败保留异常语义，可由统一执行层记录、重试或降级。",
        "真实故障可能被误判为正常无结果，导致失败率和恢复指标失真。",
    ),
    "tests/test_multi_source_retrieval.py::test_multi_source_retrieval_keeps_success_when_one_provider_fails": _description(
        "验证一个论文来源超时时，多源检索仍使用另一个成功来源。",
        "保留 OpenAlex 论文和 arXiv TIMEOUT 明细，不错误触发静态兜底。",
        "局部数据源故障可能拖垮整个检索，或掩盖成功结果与失败原因。",
    ),
    "tests/test_multi_source_retrieval.py::test_multi_source_retrieval_uses_reranker_only_when_feature_flag_is_enabled": _description(
        "验证跨来源重排只有在功能开关开启时接入真实 multi 检索流程。",
        "OpenAlex 高相关候选升到首位，并记录确定性重排策略和完整候选数。",
        "重排器可能没有进入运行时，或无法通过开关安全回滚到原有合并策略。",
    ),
    "tests/test_multi_source_retrieval.py::test_multi_source_metadata_verification_can_quarantine_unsafe_record": _description(
        "验证权威元数据校验开关接入真实多来源检索并隔离低可信身份记录。",
        "不相关标题与未经原生来源确认的 arXiv DOI 被移出候选，同时输出 v2 策略和隔离计数。",
        "校验器可能只在评测中生效而没有保护正式 LangGraph 检索流程，或关闭后无法回滚。",
    ),
    "tests/test_reranker.py::test_tokenize_handles_english_stopwords_and_chinese_characters": _description(
        "验证零 Token 重排器能稳定处理英文停用词和中文字符。",
        "英文实词与中文字符被保留，常见英文停用词被删除。",
        "中英文查询可能无法形成稳定特征，导致相关性评分失真。",
    ),
    "tests/test_reranker.py::test_metadata_verifier_detects_conflicting_arxiv_ids_and_missing_abstract": _description(
        "验证元数据校验器识别同一记录中的 arXiv ID 冲突和摘要缺失。",
        "两个风险产生明确错误码并降低元数据质量分。",
        "身份冲突或不完整论文可能以高可信度进入最终候选。",
    ),
    "tests/test_reranker.py::test_reranker_promotes_query_relevant_openalex_candidate_into_top_k": _description(
        "验证统一重排能让被 arXiv 前五条遮挡的 OpenAlex 高相关论文进入 Top K。",
        "Reflexion 论文从第二来源候选升至第一，并保留截断前候选数量。",
        "multi 仍可能只保留第一来源结果，无法获得多来源互补收益。",
    ),
    "tests/test_reranker.py::test_reranker_interleaves_equal_relevance_candidates_by_source_rank": _description(
        "验证文本相关性相同时按各来源原始排名公平交错候选。",
        "两个来源按照 A1/O1/A2/O2 排列，不再由来源列表顺序垄断 Top K。",
        "弱文本信号场景仍可能被首个来源完全占据。",
    ),
    "tests/test_reranker.py::test_cross_source_title_conflict_is_visible_and_penalized": _description(
        "验证相同 DOI 的跨来源标题严重冲突会被合并、标记并降权。",
        "重复论文只保留一条，记录两个来源及 CROSS_SOURCE_TITLE_CONFLICT。",
        "OpenAlex 等来源的异常标题可能被当成可靠元数据进入高排名。",
    ),
    "tests/test_reranker.py::test_authoritative_arxiv_record_repairs_conflicting_secondary_title": _description(
        "验证相同 arXiv 身份存在原生 arXiv 证据时使用权威字段修复二级来源冲突。",
        "即使 OpenAlex 记录先出现，最终标题也恢复为 arXiv 标题，并记录修复状态、动作和计数。",
        "合并顺序可能错误决定规范标题，让污染或过期的二级来源覆盖原生元数据。",
    ),
    "tests/test_reranker.py::test_unverified_arxiv_identity_with_unrelated_title_is_quarantined": _description(
        "验证只有二级来源声称 arXiv DOI 且标题与查询无关时执行隔离。",
        "可疑记录不会进入排序结果，隔离明细保留身份、警告和动作以供审计。",
        "伪造或错误关联的稳定 ID 可能借助身份信号进入高排名并污染答案。",
    ),
    "tests/test_reranker.py::test_unverified_but_query_supported_arxiv_identity_remains_available": _description(
        "验证尚无原生来源确认但标题与查询高度一致的二级来源记录不会被过度隔离。",
        "记录保留在候选中并标为 SECONDARY_ACCEPTED，同时提示身份仍待确认。",
        "元数据门槛可能过严而误删有价值论文，造成 Recall 回归。",
    ),
    "tests/test_retrieval_online_eval.py::test_verified_rerank_reports_quarantined_secondary_identity": _description(
        "验证在线评测为元数据校验策略单独记录隔离数量和规范身份。",
        "被隔离论文不计入返回结果，报告仍保存 arXiv 规范身份供异常追踪。",
        "评测可能遗漏校验器的实际动作，导致质量不变时无法证明异常记录已被清除。",
    ),
    "tests/test_tool_layer.py::test_arxiv_lookup_adapter_uses_native_identity_contract": _description(
        "验证工具层可以按 arXiv 原生 ID 查询单篇规范元数据，而不需要退化为关键词搜索。",
        "lookup 工具准确传递 ID，并通过统一 Pydantic 输出协议返回论文。",
        "身份校验可能误用相关性搜索结果，无法证明返回论文就是被声明的规范身份。",
    ),
    "tests/test_reranker.py::test_canonical_arxiv_evidence_repairs_secondary_claim_without_query_gate": _description(
        "验证取得原生 arXiv 证据后，身份判断不再依赖标题与用户查询的词法重合度。",
        "即使查询故意无关，身份真实的二级记录仍被规范证据确认并保留。",
        "相关性低可能继续被误判为身份造假，造成有价值论文被隔离。",
    ),
    "tests/test_reranker.py::test_canonical_arxiv_evidence_repairs_wrong_secondary_title": _description(
        "验证二级来源标题错误时使用同一 ID 的原生 arXiv 标题修复，而不是直接丢弃论文。",
        "标题和摘要恢复为规范字段，记录修复动作且论文继续参与排序。",
        "可修复的来源污染可能被保留为错误标题，或被过度隔离造成召回下降。",
    ),
    "tests/test_reranker.py::test_canonical_arxiv_not_found_is_explicit_negative_evidence": _description(
        "验证原生 arXiv 按 ID 明确查无记录时，将其作为身份声明无效的负证据。",
        "记录以 AUTHORITATIVE_NOT_FOUND 状态隔离，并保留专用警告供审计。",
        "不存在的 arXiv 身份可能因标题碰巧相关而绕过校验进入答案。",
    ),
    "tests/test_canonical_metadata_eval.py::test_collect_claimed_arxiv_ids_uses_secondary_provider_claims": _description(
        "验证候选评测能从 OpenAlex 等二级来源的 DOI 中提取待验证 arXiv 身份。",
        "不同格式 DOI 被归一为稳定 arXiv ID 清单。",
        "待验证身份可能提取不全，导致规范来源评测覆盖率虚高。",
    ),
    "tests/test_canonical_metadata_eval.py::test_canonical_fetcher_caches_successful_lookup": _description(
        "验证成功取得的规范元数据会缓存，快照重放不会重复消耗网络请求。",
        "相同 ID 只实际请求一次，第二次读取缓存并记录命中。",
        "跨快照评测可能重复请求同一论文，增加耗时和限流风险。",
    ),
    "tests/test_canonical_metadata_eval.py::test_canonical_fetcher_does_not_reuse_failed_lookup": _description(
        "验证 SSL、超时等临时失败不会被当成永久缓存结果。",
        "已有失败记录会触发重新查询，不增加成功缓存命中数。",
        "一次短暂网络失败可能永久污染评测，错误地把未验证身份当作查无记录。",
    ),
    "tests/test_canonical_metadata_eval.py::test_collect_quarantined_arxiv_ids_limits_authority_experiment": _description(
        "验证本轮候选实验只查询 v2 实际隔离过的身份，控制外部请求成本。",
        "两份快照的隔离记录被合并、去重为最小验证集合。",
        "评测可能无差别查询所有结果，增加 API 调用且偏离误伤复核目标。",
    ),
    "tests/test_canonical_metadata_eval.py::test_promotion_requires_three_complete_non_regressing_snapshots": _description(
        "验证规范元数据候选只有在三份完整独立快照、权威覆盖完整且逐题无回归时才通过晋升门槛。",
        "三份候选质量均不低于基线时 promotion_ready 为真，并记录零逐题回归。",
        "候选可能凭单次偶然提升或不完整证据进入默认流程，造成上线后质量漂移。",
    ),
    "tests/test_tool_layer.py::test_crossref_client_normalizes_doi_metadata": _description(
        "验证 Crossref 客户端正确编码 DOI，并把标题、作者、年份和链接归一为统一论文结构。",
        "带斜杠 DOI 被安全编码，Crossref 响应字段准确进入 PaperRecord。",
        "普通 DOI 查询可能因 URL 错误或字段映射错误产生伪冲突和错误修复。",
    ),
    "tests/test_tool_layer.py::test_crossref_lookup_adapter_uses_shared_lookup_contract": _description(
        "验证 Crossref 与 arXiv 共用 paper.lookup 工具能力和 Pydantic 输出契约。",
        "同一 Router、Registry、Policy 和 Executor 可以替换 authority provider。",
        "Crossref 可能变成绕过工具约束的特例，增加后续 MCP 接入和选型替换成本。",
    ),
    "tests/test_multi_source_retrieval.py::test_arxiv_authority_switch_is_independent_from_legacy_metadata_gate": _description(
        "验证 arXiv 原生身份验证可独立于旧版词法元数据开关受控启用。",
        "旧 v2 开关关闭时，独立开关仍能注入原生证据、修复标题并记录 lookup 工具。",
        "已通过三快照门槛的 v3 可能被旧综合开关绑定，无法安全灰度或单独回滚。",
    ),
    "tests/test_crossref_authority_eval.py::test_collects_only_ordinary_dois_stable_across_all_snapshots": _description(
        "验证普通 DOI 候选评测只使用所有独立快照都出现的非 arXiv DOI。",
        "不稳定记录和 arXiv DOI 被排除，保留可复现的普通出版 DOI。",
        "评测可能混入快照漂移或重复验证 arXiv 身份，导致候选覆盖结论失真。",
    ),
    "tests/test_crossref_authority_eval.py::test_crossref_eval_separates_match_conflict_not_found_and_failure": _description(
        "验证 Crossref 评测严格区分标题匹配、标题冲突、规范查无和网络失败。",
        "四类状态分别计数，失败不会被伪装成查无或元数据冲突。",
        "临时网络故障可能错误触发论文隔离，污染 authority provider 选型指标。",
    ),
    "tests/test_crossref_authority_eval.py::test_stratified_sample_round_robins_doi_prefixes": _description(
        "验证普通 DOI 样本按注册前缀轮转抽取，避免单一高频前缀垄断评测集。",
        "样本容量允许时优先覆盖不同前缀，再抽取同前缀的第二条记录。",
        "按字典序直接截取可能让 ACL 等单一出版群体主导选型结论。",
    ),
    "tests/test_crossref_authority_eval.py::test_provider_comparison_counts_only_two_successful_titles": _description(
        "验证 provider 一致率只使用双方均成功返回标题的 DOI。",
        "单方失败的记录不进入分母，双方标题一致时正确计入一致数量。",
        "限流失败可能被当成元数据不一致，错误贬低候选 provider。",
    ),
    "tests/test_tool_layer.py::test_semantic_scholar_client_normalizes_doi_metadata": _description(
        "验证 Semantic Scholar DOI 精确查询、API Key 请求头和统一论文字段映射。",
        "DOI 被安全编码，作者、年份、外部 DOI 与开放 PDF 进入 PaperRecord。",
        "替代 provider 可能因 URL 或认证错误产生系统性失败。",
    ),
    "tests/test_tool_layer.py::test_semantic_scholar_adapter_uses_shared_lookup_contract": _description(
        "验证 Semantic Scholar 与 Crossref 共用 paper.lookup 工具契约。",
        "Router 和 Executor 可以按 provider 替换实现而无需改动调用方。",
        "第二候选源可能绕过 Registry、Policy 和输出校验，破坏工具层边界。",
    ),
    "tests/test_tool_layer.py::test_semantic_scholar_client_maps_rate_limit_to_tool_error": _description(
        "验证 Semantic Scholar HTTP 429 被映射为 RATE_LIMITED。",
        "限流进入可重试失败类别，不被误记为论文查无。",
        "匿名访问限流可能污染覆盖率并错误触发论文隔离。",
    ),
    "tests/test_reranker.py::test_crossref_doi_evidence_repairs_conflicting_secondary_title": _description(
        "验证同一普通 DOI 的 Crossref 规范标题可修复明显冲突的二级来源标题。",
        "低相似度污染标题被替换，并记录 REPAIRED_TITLE_FROM_CROSSREF。",
        "普通 DOI 证据可能只被记录却无法修复实际元数据污染。",
    ),
    "tests/test_reranker.py::test_crossref_doi_not_found_is_visible_but_does_not_quarantine": _description(
        "验证 Crossref 明确查无只形成可审计警告，不自动隔离普通 DOI。",
        "记录 DOI_AUTHORITY_NOT_FOUND，论文仍保留在候选排序中。",
        "单一规范源覆盖缺口可能被误当成虚假论文证据，造成召回损失。",
    ),
    "tests/test_multi_source_retrieval.py::test_doi_authority_switch_loads_crossref_without_legacy_gate": _description(
        "验证 DOI authority 可通过独立开关接入生产多源重排。",
        "旧元数据开关关闭时仍可加载 Crossref 证据并修复污染标题。",
        "普通 DOI 校验可能与旧综合开关耦合，无法单独灰度或回滚。",
    ),
    "tests/test_multi_source_retrieval.py::test_failed_crossref_lookup_is_not_cached_or_negative_evidence": _description(
        "验证 Crossref 超时不会缓存或形成 DOI 负证据。",
        "失败被记录到工具执行明细，authority 索引和缓存保持为空。",
        "临时网络失败可能永久污染身份结论并误伤论文。",
    ),
    "tests/test_canonical_metadata_eval.py::test_collect_claimed_ordinary_dois_excludes_arxiv_doi": _description(
        "验证联合重放只把普通 DOI 交给 Crossref，排除 arXiv DOI。",
        "普通 DOI 被归一去重，arXiv DOI 继续由原生 arXiv authority 处理。",
        "同一身份可能被重复查询不同 provider，增加成本并产生冲突结论。",
    ),
    "tests/test_canonical_metadata_eval.py::test_canonical_doi_fetcher_caches_success_and_not_found": _description(
        "验证 Crossref 成功记录和明确查无均可重复使用。",
        "相同 DOI 第二次读取缓存，查无仍保持明确 NOT_FOUND 状态。",
        "三快照重放可能重复产生外部请求，增加耗时和限流风险。",
    ),
    "tests/test_canonical_metadata_eval.py::test_canonical_doi_fetcher_does_not_cache_failure": _description(
        "验证 DOI authority 网络失败不会写入成功缓存。",
        "同一 DOI 再次调用时会重试，失败计数准确累积。",
        "一次短暂故障可能被永久当成规范查无。",
    ),
    "tests/test_canonical_metadata_eval.py::test_doi_incremental_comparison_does_not_claim_unchanged_quality": _description(
        "验证 Crossref 相对仅 arXiv canonical 没有指标变化时不得宣称质量提升。",
        "质量提升标记为假，排名变化和逐题回归均为零。",
        "已有 arXiv 带来的提升可能被错误归因给普通 DOI 校验。",
    ),
    "tests/test_doi_contamination_challenge.py::test_doi_contamination_challenge_meets_stop_condition": _description(
        "验证 DOI 校验在固定污染、缺失、近似、查无和失败场景中达到阶段止损条件。",
        "6 类场景全部通过，修复准确率 100%，误修复和误隔离均为 0。",
        "DOI 议题可能在没有安全验收的情况下被草率结束，或无边界持续扩张。",
    ),
    "tests/test_parallel_retrieval.py::test_parallel_retrieval_preserves_configured_source_order": _description(
        "验证来源完成顺序不同也不会改变配置顺序和合并结果顺序。",
        "慢 arXiv 与快 OpenAlex 并发完成后仍按 arXiv、OpenAlex 顺序处理。",
        "线程完成竞态可能导致结果排序和去重行为不可复现。",
    ),
    "tests/test_parallel_retrieval.py::test_parallel_retrieval_keeps_partial_success": _description(
        "验证并行模式下单一来源空结果不影响另一来源成功返回。",
        "OpenAlex 论文仍进入 multi_source 结果，不错误触发全局兜底。",
        "一个来源异常可能取消其他来源结果，破坏原有失败恢复语义。",
    ),
    "tests/test_parallel_retrieval.py::test_single_source_does_not_create_parallel_pool": _description(
        "验证单来源检索即使并行开关开启也不创建线程池。",
        "arXiv 单来源继续走原有直接调用路径。",
        "简单请求可能承担不必要的线程调度成本。",
    ),
    "tests/test_parallel_retrieval.py::test_parallel_benchmark_reports_repeatable_speedup_and_equivalence": _description(
        "验证来源级并行在重复离线 I/O 实验中稳定降低延迟且保持结果一致。",
        "至少获得 1.5 倍加速、30% 延迟下降和 100% 结果一致率。",
        "单次偶然计时可能被误认为稳定性能提升，或并行改变业务结果。",
    ),
    "tests/test_doi_contamination_challenge.py::test_doi_contamination_challenge_meets_stop_condition": _description(
        "验证 DOI 校验在固定污染、缺失、近似、查无和失败场景中达到阶段止损条件。",
        "6 类场景全部通过，修复准确率 100%，误修复和误隔离均为 0。",
        "DOI 议题可能在没有安全验收的情况下被草率结束，或无边界持续扩张。",
    ),
    "tests/test_parallel_retrieval.py::test_parallel_retrieval_preserves_configured_source_order": _description(
        "验证来源完成顺序不同也不会改变配置顺序和合并结果顺序。",
        "慢 arXiv 与快 OpenAlex 并发完成后仍按 arXiv、OpenAlex 顺序处理。",
        "线程完成竞态可能导致结果排序和去重行为不可复现。",
    ),
    "tests/test_parallel_retrieval.py::test_parallel_retrieval_keeps_partial_success": _description(
        "验证并行模式下单一来源空结果不影响另一来源成功返回。",
        "OpenAlex 论文仍进入 multi_source 结果，不错误触发全局兜底。",
        "一个来源异常可能取消其他来源结果，破坏原有失败恢复语义。",
    ),
    "tests/test_parallel_retrieval.py::test_single_source_does_not_create_parallel_pool": _description(
        "验证单来源检索即使并行开关开启也不创建线程池。",
        "arXiv 单来源继续走原有直接调用路径。",
        "简单请求可能承担不必要的线程调度成本。",
    ),
    "tests/test_parallel_retrieval.py::test_parallel_benchmark_reports_repeatable_speedup_and_equivalence": _description(
        "验证来源级并行在重复离线 I/O 实验中稳定降低延迟且保持结果一致。",
        "至少获得 1.5 倍加速、30% 延迟下降和 100% 结果一致率。",
        "单次偶然计时可能被误认为稳定性能提升，或并行改变业务结果。",
    ),
    "tests/test_parallel_retrieval_online.py::test_online_parallel_ab_reports_latency_equivalence_and_gate": _description(
        "验证在线串行/并行 A/B 同时记录延迟、结果重合率与晋升门槛。",
        "请求数、P95、结果重合率和 acceptance_passed 均按成对实验正确计算。",
        "在线性能结论可能缺少结果等价约束，导致以质量回归换取速度。",
    ),
    "tests/test_parallel_retrieval_online.py::test_online_parallel_ab_counts_rate_limit_and_blocks_gate": _description(
        "验证外部来源限流会被单独统计并阻止并行开关晋升。",
        "RATE_LIMITED 计数完整，acceptance_passed 为 false。",
        "并行放大的限流风险可能被速度指标掩盖。",
    ),
    "tests/test_parallel_retrieval_online.py::test_online_parallel_ab_blocks_equal_fallback_results_after_network_failure": _description(
        "验证网络全失败时，即使兜底结果完全相同也不能形成假阳性。",
        "结果重合率可为 100%，但失败计数会阻止晋升。",
        "相同兜底结果可能被误认成真实检索结果等价。",
    ),
    "tests/test_parallel_retrieval_online.py::test_online_parallel_ab_rejects_invalid_budget_and_writes_report": _description(
        "验证在线评测拒绝空查询或非法预算，并能写出可审计 JSON。",
        "非法输入抛出异常，合法报告可读且查询数正确。",
        "评测可能无意产生零样本结论或无法留档。",
    ),
    "tests/test_retrieve_planning.py::test_multi_query_parallel_preserves_planned_order": _description(
        "验证子查询完成顺序不同也不会改变规划顺序与合并结果顺序。",
        "慢查询和快查询并发完成后仍按 first、second 顺序收集。",
        "并发竞态可能使复杂任务结果不可复现。",
    ),
    "tests/test_retrieve_planning.py::test_multi_query_single_query_does_not_create_pool": _description(
        "验证只有一个子查询时不创建线程池。",
        "单子查询继续走直接调用路径。",
        "简单任务可能承担不必要的并发调度成本。",
    ),
    "tests/test_parallel_retrieval_online.py::test_online_parallel_ab_reports_latency_equivalence_and_gate": _description(
        "验证在线串行/并行 A/B 同时记录延迟、结果重合率与晋升门槛。",
        "请求数、P95、结果重合率和 acceptance_passed 均按成对实验正确计算。",
        "在线性能结论可能缺少结果等价约束，导致以质量回归换取速度。",
    ),
    "tests/test_parallel_retrieval_online.py::test_online_parallel_ab_counts_rate_limit_and_blocks_gate": _description(
        "验证外部来源限流会被单独统计并阻止并行开关晋升。",
        "RATE_LIMITED 计数完整，acceptance_passed 为 false。",
        "并行放大的限流风险可能被速度指标掩盖。",
    ),
    "tests/test_parallel_retrieval_online.py::test_online_parallel_ab_blocks_equal_fallback_results_after_network_failure": _description(
        "验证网络全失败时，即使兜底结果完全相同也不能形成假阳性。",
        "结果重合率可为 100%，但失败计数会阻止晋升。",
        "相同兜底结果可能被误认成真实检索结果等价。",
    ),
    "tests/test_parallel_retrieval_online.py::test_online_parallel_ab_rejects_invalid_budget_and_writes_report": _description(
        "验证在线评测拒绝空查询或非法预算，并能写出可审计 JSON。",
        "非法输入抛出异常，合法报告可读且查询数正确。",
        "评测可能无意产生零样本结论或无法留档。",
    ),
    "tests/test_retrieve_planning.py::test_multi_query_parallel_preserves_planned_order": _description(
        "验证子查询完成顺序不同也不会改变规划顺序与合并结果顺序。",
        "慢查询和快查询并发完成后仍按 first、second 顺序收集。",
        "并发竞态可能使复杂任务结果不可复现。",
    ),
    "tests/test_retrieve_planning.py::test_multi_query_single_query_does_not_create_pool": _description(
        "验证只有一个子查询时不创建线程池。",
        "单子查询继续走直接调用路径。",
        "简单任务可能承担不必要的并发调度成本。",
    ),
    "tests/test_parallel_multi_query_eval.py::test_multi_query_parallel_benchmark_reports_gate_and_equivalence": _description(
        "验证子查询并行基准正确计算性能门槛，并保持结果与规划顺序一致。",
        "结果与规划顺序一致率为 100%，acceptance_passed 与报告中的速度门槛计算一致。",
        "基准可能错误计算晋升结论，或并发改变子查询合并语义；墙钟速度由独立 Benchmark 判定。",
    ),
    "tests/test_retrieval_replan.py::test_replan_retries_same_query_for_transient_tool_failure": _description(
        "验证超时等暂时工具错误不会被误判为查询质量问题。",
        "保持原查询重试一次，并记录失败类型、错误码和重试次数。",
        "网络故障可能触发无意义查询改写，降低恢复概率。",
    ),
    "tests/test_retrieval_replan.py::test_replan_broadens_empty_query_without_llm": _description(
        "验证零结果场景使用确定性规则放宽过窄查询。",
        "去除引号和括号并追加 research survey，不产生 LLM 调用。",
        "空结果可能原样重试，重复消耗工具预算。",
    ),
    "tests/test_retrieval_replan.py::test_replan_expands_low_relevance_query_and_records_reason": _description(
        "验证有结果但相关性低时扩展综述上下文并记录评分原因。",
        "追加 survey review，审计记录包含 low_relevance 与原评分。",
        "低相关结果可能只通过扩大数量重试而不改变检索意图。",
    ),
    "tests/test_retrieval_replan.py::test_retry_query_overrides_old_multi_query_plan": _description(
        "验证重规划查询优先于旧的多子查询计划。",
        "第二轮只执行 retry_query，不重复运行已经失败的旧计划。",
        "重规划动作可能被旧 sub_queries 遮蔽，形成伪 Replan。",
    ),
    "tests/test_retrieval_replan_eval.py::test_replan_outperforms_plain_retry_and_meets_acceptance_gate": _description(
        "验证固定故障集中 Replan 相对原样重试提升离线 Oracle 查询命中率并减少无效重试。",
        "分类准确、语义失败不再原样重试，且不调用 LLM；该结果不代表在线检索恢复率。",
        "Replan 规则可能未生成预先标注的目标修复查询，或引入额外 Token 成本。",
    ),
    "tests/test_retrieval_stop_decision.py::test_first_low_score_requests_replan": _description(
        "验证首次检索低于质量门槛时输出明确的 Replan 请求状态。",
        "outcome 为 replan_required，停止原因为 quality_below_threshold。",
        "低质量首次结果可能缺少后续动作信号而直接生成答案。",
    ),
    "tests/test_retrieval_stop_decision.py::test_second_low_score_stops_when_retry_budget_is_exhausted": _description(
        "验证第二轮仍低质量时停止并记录重试预算耗尽。",
        "outcome 为 stopped_low_quality，原因是 retry_budget_exhausted。",
        "第二轮失败可能无审计地继续循环或被误记为成功。",
    ),
    "tests/test_retrieval_stop_decision.py::test_second_high_score_records_recovery": _description(
        "验证 Replan 后质量达到门槛时记录恢复成功。",
        "outcome 为 recovered，停止原因为 quality_threshold_met。",
        "成功恢复可能无法与首轮直接通过区分，影响后续能力评测。",
    ),
    "tests/test_low_quality_generation.py::test_low_quality_stop_returns_evidence_safe_answer_without_llm": _description(
        "验证第二轮仍低质量时跳过大模型并返回证据安全的降级答复。",
        "回答明确标记证据不足、列出待核验候选，generation_skipped 为真且无 LLM 调用。",
        "系统可能把低质量证据包装成确定结论，并继续浪费生成 Token。",
    ),
    "tests/test_low_quality_generation.py::test_accepted_retrieval_keeps_normal_generation_path": _description(
        "验证质量通过的检索仍走原有 Skill/生成路径。",
        "accepted 状态正常执行技能并返回原回答。",
        "质量闸门可能误拦截正常任务，造成不必要降级。",
    ),
    "tests/test_low_quality_generation.py::test_metrics_records_recovery_budget_and_generation_mode": _description(
        "验证指标记录检索恢复、预算耗尽、回答模式和生成跳过状态。",
        "预算耗尽为真、恢复为假，answer_mode 与 generation_skipped 正确写入。",
        "降级行为可能无法审计，后续无法比较 Replan、Reflection 与普通重试。",
    ),
    "tests/test_quality_gate_eval.py::test_quality_gate_blocks_low_quality_without_false_blocks_or_llm_cost": _description(
        "验证质量闸门能阻断低质量生成，同时不误拦截正常任务并减少模拟 LLM 成本。",
        "阻断准确率和格式合规率 100%，误阻断率 0%，避免 4 次调用和 480 Token。",
        "闸门可能漏放低质量证据、误阻断正常回答，或没有产生实际成本收益。",
    ),
    "tests/test_rag_eval_models.py::test_rag_dataset_accepts_versioned_grounded_case": _description(
        "验证本地 RAG 评测数据能记录版本化问题、答案、证据片段、页码和来源。",
        "合法数据通过校验，语料版本与证据页码可审计。",
        "RAG 实验可能缺少可复现语料版本或人工证据依据。",
    ),
    "tests/test_rag_eval_models.py::test_rag_dataset_rejects_invalid_pages_and_duplicate_evidence": _description(
        "验证错误页码和重复证据身份会被评测契约拒绝。",
        "页码倒置或跨案例重复 document/chunk 身份均触发 ValidationError。",
        "脏标注可能污染 Recall、引用定位和技术选型结论。",
    ),
    "tests/test_rag_eval_models.py::test_rag_experiment_config_keeps_technology_choices_replaceable": _description(
        "验证 Dense 与 Graph 等 RAG 技术通过统一配置字段替换，而非写死实现。",
        "不同 retriever family、Embedding、Store 和 Graph Retriever 可使用独立 config_id。",
        "项目可能在评测前绑定单一产品，无法进行公平单变量对照。",
    ),
    "tests/test_local_rag_foundation.py::test_fixed_window_chunker_preserves_page_and_overlap": _description(
        "验证固定窗口分块保留页码、字符位置和配置的重叠区间。",
        "分块文本和 char_start 正确，所有片段仍定位到原 PDF 页。",
        "全文检索结果可能无法回溯页码，或分块边界丢失上下文。",
    ),
    "tests/test_local_rag_foundation.py::test_fixed_window_chunker_rejects_invalid_parameters": _description(
        "验证重叠长度不能等于或超过分块长度。",
        "非法参数触发 ValueError，避免零步长或无限循环。",
        "错误 Chunk 配置可能造成挂起、重复片段或不可控索引体积。",
    ),
    "tests/test_local_rag_foundation.py::test_manifest_rebuilds_only_for_content_or_processing_version_change": _description(
        "验证知识库只在 PDF 内容、Parser 或 Chunker 版本变化时局部重建。",
        "相同哈希与版本跳过，内容或处理版本变化触发 rebuild。",
        "每次更新可能全库重建，或变化论文没有刷新造成旧证据。",
    ),
    "tests/test_local_rag_foundation.py::test_manifest_writer_keeps_corpus_version_and_status": _description(
        "验证语料清单记录 corpus_version 和每篇论文的处理状态。",
        "JSON 清单可读，版本和 pending 状态完整保存。",
        "知识库更新可能失去语料版本与处理进度，无法复现实验。",
    ),
    "tests/test_local_rag_corpus_manifest.py::test_build_corpus_manifest_preserves_declared_identity_and_hash": _description(
        "验证代表论文来源清单生成 Manifest 时保留语料版本、论文身份和内容哈希。",
        "输出包含唯一论文、arXiv ID 和 64 位 SHA-256，可追踪实验实际使用的原始文件。",
        "语料身份或内容版本可能丢失，导致不同 RAG 方案无法在同一批论文上公平复现。",
    ),
    "tests/test_local_rag_corpus_manifest.py::test_build_corpus_manifest_rejects_missing_declared_pdf": _description(
        "验证来源清单声明的 PDF 缺失时立即失败，而不是静默生成不完整语料。",
        "异常明确列出缺失文件名，避免误把缺论文的实验结果当成完整结果。",
        "测试语料可能悄悄缩水，召回率和跨论文问题会得到具有误导性的结果。",
    ),
    "tests/test_rag_eval_models.py::test_rag_dataset_allows_different_questions_to_share_evidence_chunk": _description(
        "验证不同问题可以引用同一个真实证据块，同时仍禁止单个问题内部重复登记证据。",
        "两个独立问题共享同一 document_id/chunk_id 时数据集通过校验。",
        "契约会迫使标注者制造虚假 chunk ID，或无法表达一段原文支持多个问题的真实情况。",
    ),
    "tests/test_rag_gold_dataset.py::test_rag_gold_v1_has_balanced_corpus_and_question_coverage": _description(
        "验证首版人工金标准包含 16 题、覆盖全部 8 篇论文，并具有多种题型和两档难度。",
        "语料、题型与难度覆盖满足首版设计矩阵，避免评测只偏向单篇或单类问题。",
        "金标准可能遗漏论文或题型过于单一，使后续 BM25、Dense 与图检索对比失真。",
    ),
    "tests/test_rag_gold_dataset.py::test_rag_gold_v1_evidence_is_present_on_declared_pdf_page": _description(
        "逐题重新解析真实 PDF，验证人工证据原文确实存在于声明的 PDF 页序号。",
        "16 题的证据片段与页码全部可回溯到本地原始论文。",
        "参考答案可能引用错误页、错误论文或经过改写而无法核验的伪证据。",
    ),
    "tests/test_rag_gold_dataset.py::test_rag_gold_builder_reproduces_committed_dataset": _description(
        "验证人工规格、PDF、Parser 与 Chunker 可确定性重建已提交的金标准 JSON。",
        "重建结果逐字段等于版本控制中的数据集，包括真实 chunk ID 与证据片段。",
        "标注产物可能不可复现，或处理组件变化后证据坐标已悄悄失效。",
    ),
    "tests/test_local_rag_bm25.py::test_mixed_tokenizer_supports_chinese_and_english_queries": _description(
        "验证 BM25 基线能把中文问题与英文术语、数字混合分词。",
        "输出同时包含英文词、中文单字/双字和实验数值，支持中文提问检索英文论文。",
        "跨语言术语或数值可能完全不进入索引，导致检索结果与算法质量无关地失败。",
    ),
    "tests/test_local_rag_bm25.py::test_bm25_ranks_matching_chunk_first_and_is_deterministic": _description(
        "验证 BM25 将包含查询词的文本块排在无关块之前，且重复运行排名与分数一致。",
        "相关块排名第一、得分更高，两次检索结果逐项相同。",
        "BM25 公式、排序方向或并列规则可能错误，使基线不可复现或相关结果后移。",
    ),
    "tests/test_local_rag_bm25.py::test_bm25_rejects_invalid_configuration_and_limit": _description(
        "验证 BM25 拒绝空语料和非正数返回条数。",
        "非法配置明确抛出 ValueError，不产生空索引或误导性排名。",
        "评测可能在没有语料或错误 K 值时静默运行并输出无意义指标。",
    ),
    "tests/test_local_rag_bm25.py::test_local_rag_metrics_use_exact_gold_chunk_rank": _description(
        "用手工可计算的排名验证本地 RAG Recall、MRR 与 nDCG 公式。",
        "金标准位于第二名时 Recall@1 为 0、Recall@3 为 1、MRR 为 0.5、nDCG 为 0.63093。",
        "指标公式或排名下标可能错误，导致后续技术选型基于虚假的提升数据。",
    ),
    "tests/test_local_rag_query_rewrite.py::test_query_expansion_preserves_original_and_adds_auditable_terms": _description(
        "验证规则查询扩展保留原问题，并把命中的中文科研术语追加为可审计英文术语。",
        "短期记忆和长期记忆分别扩展为对应英文表达，且返回明确的来源到目标映射。",
        "查询可能丢失用户原意、产生不可追踪改写，或无法跨越中英文词汇鸿沟。",
    ),
    "tests/test_local_rag_query_rewrite.py::test_query_expansion_is_deterministic_and_leaves_unknown_query_unchanged": _description(
        "验证未登记术语不被猜测改写，并且相同输入的扩展结果完全一致。",
        "未知问题原样返回，已知术语重复运行得到相同查询和匹配记录。",
        "规则可能过度改写未知问题或产生不稳定结果，使 A/B 对照不可复现。",
    ),
    "tests/test_local_rag_bm25.py::test_local_rag_metrics_do_not_double_count_duplicate_page_hits": _description(
        "验证同一相关 PDF 页返回多个 Chunk 时，page-level 指标只计算首次命中。",
        "重复页的 Recall、MRR、nDCG 均不超过 1，nDCG 恰为 1。",
        "同一页可能被重复计分，导致 nDCG 大于 100% 并制造虚假检索提升。",
    ),
    "tests/test_rag_holdout_dataset.py::test_holdout_has_ten_cases_and_no_development_evidence_pages": _description(
        "验证独立保留集包含 10 题、覆盖全部 8 篇论文，并且证据页不与开发集重叠。",
        "保留集与开发集页面集合完全不相交，可用于检查冻结术语表的初步泛化。",
        "保留题可能复用术语表设计时已见证据，导致把开发集拟合误判为泛化收益。",
    ),
    "tests/test_rag_holdout_dataset.py::test_holdout_evidence_is_present_on_declared_pdf_page": _description(
        "逐题重新解析真实 PDF，验证保留集证据原文存在于声明页面。",
        "10 个保留问题的原文片段和页码均可回溯到本地论文。",
        "保留集可能含错误页码或不可核验的证据，使泛化评测失去可信基础。",
    ),
    "tests/test_rag_holdout_dataset.py::test_holdout_builder_reproduces_frozen_json": _description(
        "验证保留集可由冻结人工规格、PDF 和固定 Chunker 确定性重建。",
        "重建 JSON 与已提交保留集逐字段一致。",
        "评测输入可能漂移，无法确认不同检索方案是否使用同一保留集。",
    ),
    "tests/test_rag_holdout_v2_dataset.py::test_holdout_v2_has_eight_papers_and_no_v1_evidence_pages": _description(
        "验证门控验证集 v2 覆盖全部 8 篇论文，且证据页与开发集及 holdout v1 完全不重叠。",
        "v2 恰含 8 题和 8 篇论文，所有证据页均为此前未见页面。",
        "复用已查看证据页会造成验证集泄漏，无法证明门控泛化。",
    ),
    "tests/test_rag_holdout_v2_dataset.py::test_holdout_v2_quotes_equal_declared_chunks": _description(
        "验证 v2 每条人工引文与当前 Parser/Chunker 生成的声明 Chunk 完全一致。",
        "Chunk 身份、论文、页码和引文文本一一对应。",
        "错误页码或切分漂移会使 Recall 指标基于不存在的证据。",
    ),
    "tests/test_rag_holdout_v2_dataset.py::test_holdout_v2_builder_reproduces_frozen_json": _description(
        "验证 v2 构建脚本能够从冻结标注和语料确定性重建提交的数据集。",
        "重新生成的 JSON 与仓库版本逐字段一致。",
        "手工编辑或非确定生成会破坏数据集版本和实验复现性。",
    ),
    "tests/test_local_rag_gated_hybrid_v2_eval.py::test_gated_v2_outcomes_count_improvements_regressions_and_unchanged": _description(
        "验证冻结门控在 v2 上的逐题对照能正确区分提升、回归和不变。",
        "三种结果各被准确计数一次，并保留逐题差值。",
        "错误的逐题归类会让平均指标掩盖真实回归并误导晋升判断。",
    ),
    "tests/test_local_rag_gated_hybrid_stability.py::test_gated_hybrid_stability_requires_deterministic_routes_and_rankings": _description(
        "验证门控 Hybrid 的三次独立进程必须保持质量、Top-5、分数和路由决定一致，且平均查询延迟 CV 不超过 50%。",
        "三次配置与缓存一致、路由和排名完全复现、延迟 CV 通过时，稳定性闸门通过。",
        "单次运行可能掩盖非确定性排序、路由漂移或偶发性能波动。",
    ),
    "tests/test_local_rag_gated_hybrid_stability.py::test_gated_hybrid_stability_rejects_route_drift": _description(
        "验证即使质量数字和延迟相同，只要独立进程的 Dense/Hybrid 路由发生漂移就必须拒绝晋升。",
        "任一次路由与基准不同都会令稳定性判定失败。",
        "路由不稳定会造成线上成本和结果不可预测，不能只看聚合质量指标。",
    ),
    "tests/test_local_rag_rewrite_ab.py::test_holdout_ab_detects_rank_regression_when_recall_at_five_is_unchanged": _description(
        "验证查询扩展即使保持 Recall@5，也会因相关证据排名下降而被标记为逐题回归。",
        "保留集 Recall@5 差值为 0、nDCG@5 差值为负，且至少记录一个 regressed 用例。",
        "逐题结论可能只看是否进入 Top5，掩盖证据从前排下滑的真实排序损失。",
    ),
    "tests/test_local_rag_dense.py::test_dense_retriever_normalizes_vectors_and_ranks_by_cosine": _description(
        "验证 Dense 检索显式归一化向量，并按余弦相似度将语义匹配块排在前面。",
        "相关块得分为 1 且排名第一，无关正交块得分为 0。",
        "未归一化裸点积可能受向量长度支配，产生不正确或不可比较的 Dense 排名。",
    ),
    "tests/test_local_rag_dense.py::test_dense_retriever_rejects_zero_vectors_and_invalid_inputs": _description(
        "验证 Dense 检索拒绝零向量和空语料。",
        "非法输入明确抛出 ValueError，避免除零或空索引生成伪结果。",
        "余弦归一化可能产生 NaN，或空知识库静默输出无意义评测。",
    ),
    "tests/test_local_rag_dense.py::test_dense_index_cache_round_trips_vectors_and_invalidates_changed_corpus": _description(
        "验证 Dense 向量缓存可以无损加载，并在语料文本、模型或处理版本变化后使用不同指纹。",
        "加载向量保持单位长度；变更语料不会错误命中旧缓存。",
        "陈旧向量可能与当前 Chunk 错位，使评测和生产检索返回不可追踪的错误证据。",
    ),
    "tests/test_local_rag_dense.py::test_dense_retriever_reuses_cached_vectors_without_document_embedding": _description(
        "验证缓存命中时 DenseRetriever 不会重新编码全部论文，只对查询生成向量。",
        "构造阶段复用缓存，搜索阶段仅调用一次查询 Embedding。",
        "每次启动仍重复编码 1098 个 Chunk，持久化缓存无法降低冷启动成本。",
    ),
    "tests/test_local_rag_dense.py::test_dense_warmup_is_fixed_and_excluded_from_formal_timing": _description(
        "验证 Dense 正式评测前执行固定次数的查询预热，并将预热延迟与正式查询指标明确隔离。",
        "预热执行两次、逐次记录耗时，且报告明确标记不计入正式计时。",
        "ONNX 首次推理初始化可能混入测试集延迟，制造虚假的性能波动。",
    ),
    "tests/test_local_rag_dense_compare.py::test_dense_comparison_uses_holdout_quality_and_keeps_production_off": _description(
        "验证 Dense 晋升判断以独立保留集质量为依据，并与生产默认开关分离。",
        "保留集 Recall@5 提升 20 个百分点且 nDCG 为正，但存在 3 个逐题回归，超过最多 2 个的门槛，因此候选晋升和生产默认均保持关闭。",
        "系统可能再次依据开发集拟合晋升，或未经重复验证就直接改动生产检索路径。",
    ),
    "tests/test_local_rag_dense_cache_compare.py::test_dense_cache_comparison_requires_same_quality_and_faster_warm_build": _description(
        "验证 Dense 缓存只有在冷启动未命中、热启动命中、质量完全一致且建库耗时下降超过 99% 时才通过。",
        "缓存被确认只改变启动成本，不改变 Recall、MRR、nDCG 或生产开关。",
        "缓存可能悄悄改变排序结果，或速度收益不足却被错误判定为可用。",
    ),
    "tests/test_local_rag_dense_stability.py::test_dense_stability_requires_three_deterministic_warm_processes": _description(
        "验证 Dense 稳定性晋升至少需要三个独立热启动进程，并同时满足缓存命中、质量一致、Top-5 与分数确定性和延迟波动门槛。",
        "三个运行的检索结果完全一致，查询延迟变异系数不超过 50%，但生产开关仍保持关闭。",
        "单次偶然结果或不稳定排名可能被错误当成可复现能力，导致后续模型对照失去公平基线。",
    ),
    "tests/test_local_rag_dense_stability.py::test_dense_stability_rejects_mixed_or_unexpected_models": _description(
        "验证稳定性评测拒绝混入其他 Embedding 模型或不符合预期模型身份的运行文件。",
        "只有全部运行来自同一指定模型时，稳定性才可能通过。",
        "MiniLM 与 MPNet 结果误混可能制造虚假的稳定性结论或错误的耗时统计。",
    ),
    "tests/test_local_rag_dense_stability_compare.py::test_stability_comparison_preserves_failed_candidate_decision": _description(
        "验证 MiniLM/MPNet 稳定性并列比较保留 MPNet 的失败判定，不因平均质量收益或模型间比值覆盖原始闸门。",
        "报告展示性能倍数，但 MPNet CV 超限时仍保持稳定性未通过和生产关闭。",
        "跨模型汇总可能错误抹平单模型波动，使失败候选绕过稳定性门槛。",
    ),
    "tests/test_local_rag_dense_warmup_compare.py::test_warmup_comparison_requires_failed_before_and_passed_after": _description(
        "验证预热对照只在同一模型由预热前失败转为预热后通过时，才判断首次初始化解释了稳定性问题。",
        "报告正确计算均值和 CV 变化，并将下一步推进到 Hybrid 互补实验。",
        "仅凭一次更快结果可能错误归因预热效果，或绕过稳定性门槛。",
    ),
    "tests/test_local_rag_hybrid.py::test_rrf_rewards_cross_retriever_agreement_without_mixing_raw_scores": _description(
        "验证 Hybrid 使用倒数排名融合奖励 BM25 与 Dense 共同命中的证据，而不直接相加尺度不同的原始分数。",
        "两个检索器都返回的 Chunk 通过名次贡献叠加排到首位，分数符合 RRF 公式。",
        "直接混合 BM25 与余弦分数会被某一分值尺度主导，导致融合不可解释。",
    ),
    "tests/test_local_rag_hybrid.py::test_rrf_is_deterministic_and_rejects_invalid_configuration": _description(
        "验证 RRF 参数必须为正，并在融合分数相同时按确定性身份规则打破平局。",
        "非法配置被拒绝，相同输入始终产生相同排序。",
        "不稳定平局或无效参数会使重复评测和缓存结果不可比较。",
    ),
    "tests/test_local_rag_hybrid.py::test_confidence_gate_defaults_to_dense_and_audits_hybrid_trigger": _description(
        "验证置信度门控默认使用 Dense，仅在 Top-1 分数和间隔同时低于冻结阈值时触发 Hybrid，并记录路由依据。",
        "低置信度小间隔查询进入 Hybrid，高置信度查询保持 Dense，两个决策均可审计。",
        "无条件融合会重现已知回归，缺少决策记录则无法解释线上检索路径。",
    ),
    "tests/test_local_rag_hybrid.py::test_confidence_gate_reuses_dense_results_when_hybrid_is_triggered": _description(
        "验证低置信度查询触发 Hybrid 后复用门控阶段已经计算的 Dense 排名，不对同一查询重复执行向量检索。",
        "一次查询只调用一次 Dense，并额外调用一次 BM25；路由记录为 Hybrid。",
        "若 Dense 被调用两次，会重复进行查询向量编码，增加平均延迟和 P95 尾延迟。",
    ),
    "tests/test_local_rag_hybrid_eval.py::test_hybrid_parameter_selection_uses_frozen_quality_first_order": _description(
        "验证 Hybrid 参数只按预先冻结的开发集规则选择：Recall@5、nDCG@5、回归数、延迟、较小 RRF k。",
        "质量指标优先于速度，候选并列时按固定顺序确定唯一参数。",
        "事后改变选参顺序或使用保留集调参会造成测试集泄漏和虚假提升。",
    ),
    "tests/test_local_rag_hybrid_gate.py::test_gate_features_use_only_runtime_rankings_and_scores": _description(
        "验证 Hybrid 门控特征只来自请求时可见的 Dense 分数、分数间隔和两路 Top-5 重合度。",
        "特征计算正确，且不读取用例 ID、主题名称或金标准答案。",
        "使用题目身份或人工标签作为线上特征会造成不可泛化的数据泄漏。",
    ),
    "tests/test_local_rag_hybrid_gate.py::test_gate_audit_rejects_rules_with_regression_or_insufficient_gain": _description(
        "验证门控审计拒绝任何触发回归或提升样本不足的规则。",
        "即使规则能改善部分题，只要同时损害其他题就不能晋升。",
        "小样本阈值可能通过挑选收益题制造虚假门控能力。",
    ),
    "tests/test_local_rag_dense_models.py::test_dense_model_matrix_changes_only_declared_embedding_properties": _description(
        "验证第二 Dense 模型通过同一评测入口配置，只声明模型自身的维度、输入长度、池化和配置身份差异。",
        "MiniLM 与 MPNet 共用语料、Chunker、相似度、缓存和指标逻辑，未知模型被拒绝。",
        "复制评测代码或接受任意模型可能引入口径漂移，使模型质量对比失去单变量意义。",
    ),
    "tests/test_local_rag_dense_model_compare.py::test_dense_model_comparison_prefers_quality_gain_without_excess_regression": _description(
        "验证第二 Dense 模型只有在保留集 nDCG 提升、Recall 不下降且逐题回归不超过 2 个时才成为首选候选。",
        "模型候选可以晋升，但生产默认开关仍独立保持关闭。",
        "只看平均指标或速度可能掩盖逐题回归，或者把模型候选误当成生产上线。",
    ),
    "tests/test_local_rag_integration.py::test_local_rag_mode_enters_main_retrieval_flow": _description(
        "验证本地全文 RAG 已接入 LangGraph 主检索入口，并保留 Chunk、页码和门控路由信息。",
        "配置 local_rag 后无需调用在线论文源即可返回本地全文证据，并展示 Dense/Hybrid 路由。",
        "若失败，本地 RAG 仍只是独立实验代码，无法作为项目主流程能力展示。",
    ),
    "tests/test_local_rag_integration.py::test_retrieve_node_exposes_local_rag_route_in_metadata": _description(
        "验证检索节点把本地 RAG 模式、排名策略和路由决定写入工作流响应元数据。",
        "API 或演示界面可以直接展示本次查询采用的检索后端和门控路径。",
        "若元数据丢失，虽然检索能够运行，但无法体现 LangGraph 编排与可审计路由特色。",
    ),
    "tests/test_demo_page.py::test_demo_page_is_served_from_fastapi_root": _description(
        "验证 FastAPI 首页能够直接提供 PaperAgent Web 演示页，并正确引用前端脚本。",
        "启动 Uvicorn 后访问根路径即可打开项目演示入口。",
        "若失败，API 虽可用但简历展示页无法访问。",
    ),
    "tests/test_demo_page.py::test_paper_formatter_keeps_local_rag_evidence_fields": _description(
        "验证服务层不会丢弃本地 RAG 的页码、Chunk ID 和检索分数。",
        "Web 页面可以展示证据来源和可审计定位信息。",
        "若失败，前端只能展示论文摘要，无法体现全文 RAG 的证据追踪能力。",
    ),
    "tests/test_demo_page.py::test_demo_page_exposes_research_agent_trace_panels": _description(
        "验证FastAPI演示页包含Research工作流、计划、执行波次、Evidence和质量闸门面板。",
        "面试演示可以直接展示研究型Agent的核心执行闭环。",
        "若失败，新增后端能力无法通过现有Web入口直观展示。",
    ),
    "tests/test_demo_page.py::test_demo_script_consumes_existing_research_metadata_contract": _description(
        "验证前端复用/chat已有Research Metadata字段渲染执行轨迹。",
        "展示层不会增加新的LLM调用或维护第二套后端状态。",
        "若失败，前端可能与生产工作流字段脱节或产生额外成本。",
    ),
    "tests/test_demo_page.py::test_demo_page_offers_zero_api_frozen_research_trace": _description(
        "验证演示页可以加载冻结L3研究轨迹而不调用/chat、外部检索或模型。",
        "面试现场即使网络波动也能展示Plan、Evidence和质量闸门。",
        "若失败，项目核心架构演示仍依赖外部服务实时可用。",
    ),
    "tests/test_mcp_adapter.py::test_readonly_mcp_tool_uses_existing_registry_policy_and_executor": _description(
        "验证只读 MCP 工具可以注册到现有 Tool Registry，并复用 Policy、Executor、Pydantic 校验和统一 ToolResult。",
        "MCP 调用成功映射为标准输出，同时记录 Server、版本、传输方式和远程工具名。",
        "若失败，MCP 会形成独立旁路，破坏统一工具层和可审计性。",
    ),
    "tests/test_mcp_adapter.py::test_mcp_adapter_preserves_validation_and_rejects_remote_errors": _description(
        "验证 MCP 适配器保留本地参数校验，并把远程错误转换为统一执行错误。",
        "无效参数不会发送给 MCP Server，远程失败也不会伪装成成功结果。",
        "若失败，不可信参数或 MCP 错误可能绕过工具执行约束进入工作流。",
    ),
    "tests/test_mcp_adapter.py::test_mcp_adapter_understands_sdk_snake_case_error_result": _description(
        "验证通用MCP Adapter识别新版SDK对象中的is_error和文本错误内容。",
        "真实MCP网络或服务错误会转成统一ToolResult，而不是被误当作结构化成功结果。",
        "若失败，外部MCP故障可能表现为误导性的Pydantic输出校验错误。",
    ),
    "tests/test_mcp_stdio_integration.py::test_real_stdio_mcp_server_returns_local_paper_catalog": _description(
        "验证 PaperAgent 通过官方 MCP SDK 和 stdio 真正启动只读 Server、完成协议调用并返回本地论文目录。",
        "真实 MCP 调用返回 ReAct 论文，并记录 stdio 传输和 Server 身份。",
        "若失败，项目只有适配器单元测试，不能证明真实 MCP 协议链路可用。",
    ),
    "tests/test_mcp_stdio_integration.py::test_real_stdio_mcp_server_is_registered_in_default_runtime": _description(
        "验证真实 MCP 目录工具已经进入 PaperAgent 默认 Tool Registry，且风险等级保持只读。",
        "主工作流可发现该工具，同时 Tool Policy 仍能按只读权限管理。",
        "若失败，MCP Server 虽能单独运行但尚未接入项目统一工具运行时。",
    ),
    "tests/test_research_skills.py::test_structured_outputs_reject_missing_required_research_content": _description(
        "验证文献综述和论文批判 Pydantic 契约拒绝空范围、空研究版图或空贡献。",
        "无实质内容的科研结构化结果无法进入后续 Scheduler、Evidence Store 或报告节点。",
        "若失败，格式合法但内容为空的结果可能被误当成科研能力成功。",
    ),
    "tests/test_research_skills.py::test_l3_primary_skill_routes_to_literature_review": _description(
        "验证 L3 Research Analysis 中经过白名单校验的 primary_skill 能实际选择 Literature Review Skill。",
        "复杂研究任务从规划层进入专门综述生成路径。",
        "若失败，Research Analyzer 虽生成 Skill 建议，但执行层仍只会运行普通回答 Skill。",
    ),
    "tests/test_research_skills.py::test_unknown_or_non_l3_research_skill_cannot_override_fast_path": _description(
        "验证未知 Skill 和 L1 普通问题不能覆盖确定性的快速路由。",
        "只有白名单内的 L3 科研 Skill 可以升级执行模式。",
        "若失败，模型字段可能触发不存在或不必要的高成本能力。",
    ),
    "tests/test_research_skills.py::test_research_prompts_expose_contract_and_evidence_guardrails": _description(
        "验证综述与批判 Prompt 同时暴露目标 Schema、证据定位要求和禁止猜测约束。",
        "模型生成前能够看到明确的科研结构与证据边界。",
        "若失败，模型容易输出不可审计的自由文本或无依据批评。",
    ),
    "tests/test_llm_online_eval.py::test_online_dataset_is_frozen_unique_and_covers_three_levels": _description(
        "验证正式在线 LLM 数据集被冻结、编号唯一并同时覆盖 L1、L2、L3。",
        "在线能力报告基于稳定且有层次覆盖的七个代表案例。",
        "若失败，数据集可能被意外清空、重复计数或只展示复杂任务。",
    ),
    "tests/test_llm_online_eval.py::test_core_online_dataset_has_30_stratified_cases_and_valid_fixtures": _description(
        "验证正式核心在线集恰好包含30题，覆盖任务分析、查询规划和八个科研生成案例。",
        "所有生成案例都能从冻结 fixture 展开出可追溯论文证据。",
        "若失败，正式集可能数量虚标、模块覆盖失衡或引用不存在的证据。",
    ),
    "tests/test_llm_online_eval.py::test_analysis_evaluator_reports_each_failed_check": _description(
        "验证在线分析判分器分别检查等级、Skill、计划有效性、调用预算和调用失败。",
        "任何关键约束失败都会在报告中明确显示，不能被总体文本掩盖。",
        "若失败，错误的研究规划可能仍被汇总为测试通过。",
    ),
    "tests/test_llm_online_eval.py::test_generation_evaluator_checks_route_structure_evidence_and_cost": _description(
        "验证在线生成判分器同时检查 Skill 路由、内容结构、论文身份和 LLM 调用成本。",
        "只有结构完整、证据可辨认且调用次数合规的真实模型回答才能通过。",
        "若失败，冗长但偏题、无证据或成本异常的回答可能被误判为成功。",
    ),
    "tests/test_research_analysis.py::test_representative_papers_alone_remains_a_simple_search": _description(
        "验证“代表论文”单独出现时只是证据要求，不会把一次检索误升级为方向研究。",
        "简单论文检索保持 L1、QA Skill 和零研究分析 LLM 调用。",
        "若失败，常见检索请求会增加不必要的规划、Token 和延迟。",
    ),
    "tests/test_research_analysis.py::test_l3_rule_fallback_preserves_time_trend_and_gap_constraints": _description(
        "验证L3结构化分析回退时从原问题保留时间范围、趋势、代表论文和研究空白。",
        "即使模型输出解析失败，Research Brief与Plan仍包含用户的关键研究约束。",
        "若失败，恢复路径虽然可运行，但会悄悄改变用户研究目标。",
    ),
    "tests/test_research_analysis.py::test_llm_analysis_accepts_thinking_text_and_fenced_json": _description(
        "验证Research Analyzer能够解析模型返回的thinking标签、解释文字和Markdown fenced JSON。",
        "结构化分析仍通过Pydantic校验并保留真实Token记录。",
        "若失败，兼容模型的合法包装格式会触发不必要的规则回退。",
    ),
    "tests/test_llm_online_eval.py::test_report_only_regrades_existing_generation_without_calling_llm": _description(
        "验证判分规则修正后能够复用已付费的模型原始输出重新判分。",
        "报告门槛变更不会强迫用户重复调用模型。",
        "若失败，测试框架自身的小修改会造成不必要的 API 成本。",
    ),
    "tests/test_llm_online_eval.py::test_provider_failure_is_not_reported_as_capability_failure": _description(
        "验证限流、连接等模型服务失败与 Agent 输出质量失败分开记录。",
        "报告保留 Provider 错误类型，不把基础设施波动误判为能力退化。",
        "若失败，项目无法判断应修代码、改 Prompt 还是等待外部服务恢复。",
    ),
    "tests/test_llm_online_eval.py::test_provider_retry_does_not_overwrite_existing_capability_result": _description(
        "验证定向重跑遇到Provider失败时只追加尝试历史，不覆盖已有正式能力结论。",
        "基线结果、Token口径和失败归因保持稳定。",
        "若失败，外部服务波动会篡改历史评测结论并造成指标不可比较。",
    ),
    "tests/test_clarification.py::test_unique_memory_candidate_resolves_reference_without_llm": _description(
        "验证只有一个活跃论文候选时，Clarification Gate零LLM自动替换指代。",
        "补全后的问题继续正常研究流程，并记录解析对象与完整查询。",
        "若失败，明确上下文仍会造成不必要的询问或错误检索。",
    ),
    "tests/test_clarification.py::test_multiple_candidates_request_clarification_and_short_circuit": _description(
        "验证存在多个可能对象时主动列出候选并短路后续执行。",
        "系统不调用LLM、不检索，也不擅自猜测其中一个对象。",
        "若失败，错误指代会扩散到规划、工具调用和最终报告。",
    ),
    "tests/test_clarification.py::test_missing_candidate_requests_explicit_object_name": _description(
        "验证指代存在但记忆中没有候选时要求用户补充论文、方法或模型名称。",
        "无法消解的问题不会作为检索关键词继续执行。",
        "若失败，系统可能搜索“这个方法”等无意义文本。",
    ),
    "tests/test_clarification.py::test_followup_candidate_restores_pending_query": _description(
        "验证用户回复候选名称后恢复原pending query、替换指代并清除等待状态。",
        "澄清对话能够跨轮继续原研究任务。",
        "若失败，主动询问会成为无法恢复的流程终点。",
    ),
    "tests/test_graph_integration.py::test_ambiguous_reference_ends_before_research_and_retrieval": _description(
        "验证Clarification Gate在LangGraph主图中位于Research Analyzer和检索之前。",
        "歧义请求以零LLM、零检索返回澄清答案。",
        "若失败，节点单测虽通过，但主工作流仍可能绕过澄清门控。",
    ),
    "tests/test_research_scheduler.py::test_scheduler_builds_bounded_dependency_waves": _description(
        "验证Research Plan按依赖编译为有界执行波次，每个波次最多包含两个任务。",
        "独立检索可受控并行，综合任务只能排在依赖检索之后。",
        "若失败，研究任务可能无界并发，或在证据尚未收集时提前综合。",
    ),
    "tests/test_research_scheduler.py::test_scheduler_reports_blocked_dependencies_instead_of_looping": _description(
        "验证未知依赖或循环依赖会返回blocked_dependencies，而不是持续调度。",
        "错误计划能够确定性停止并保留可诊断状态。",
        "若失败，无效计划可能形成无法终止的Agent Loop。",
    ),
    "tests/test_research_scheduler.py::test_evidence_store_deduplicates_and_preserves_provenance": _description(
        "验证Evidence Store按论文身份去重，并保留来源、定位符和关联研究任务。",
        "相同证据只计一次，后续回答仍可追溯到原始论文。",
        "若失败，重复论文会虚增证据量，或结论无法定位来源。",
    ),
    "tests/test_research_scheduler.py::test_synthesis_task_receives_claim_evidence_inputs": _description(
        "验证综合任务从依赖任务接收证据ID集合，而不是脱离证据直接生成结论。",
        "后续Writer和Coverage Gate可按声明检查证据覆盖。",
        "若失败，研究报告可能出现没有论文支撑的综合判断。",
    ),
    "tests/test_research_scheduler.py::test_non_l3_nodes_leave_fast_path_unchanged": _description(
        "验证L1/L2请求不会启用Research Scheduler和Evidence Store。",
        "普通问答继续使用低延迟、低Token的快速路径。",
        "若失败，简单输入也会承担研究型工作流的额外成本。",
    ),
    "tests/test_research_coverage_writer.py::test_coverage_gate_passes_only_fully_supported_claims": _description(
        "验证所有综合声明的依赖任务都有证据时Coverage Gate判定通过。",
        "Research Writer只在核心结论具备完整证据输入时正常生成。",
        "若失败，完整证据可能被误阻断，或缺失证据被错误放行。",
    ),
    "tests/test_research_coverage_writer.py::test_coverage_gate_reports_partial_missing_dependencies": _description(
        "验证部分声明缺证据时记录覆盖率、未覆盖声明和缺失任务。",
        "Writer可以保留有证据内容，并对缺失部分明确降级。",
        "若失败，部分覆盖会被粗暴视为全通过或全失败。",
    ),
    "tests/test_research_coverage_writer.py::test_coverage_gate_blocks_when_no_claim_has_evidence": _description(
        "验证没有任何综合声明获得证据时禁止Research Writer运行。",
        "零覆盖研究任务不会消耗模型Token生成无依据报告。",
        "若失败，模型可能在没有证据时补写研究结论。",
    ),
    "tests/test_research_coverage_writer.py::test_non_research_coverage_keeps_fast_path_available": _description(
        "验证普通任务未启用Evidence Store时Coverage Gate标记为不适用。",
        "L1/L2快速路径不会被研究报告证据门控阻断。",
        "若失败，普通论文问答可能无法进入原有生成流程。",
    ),
    "tests/test_research_coverage_writer.py::test_writer_prompt_contains_only_stable_evidence_contract": _description(
        "验证Research Writer Prompt包含稳定证据ID、定位符和未覆盖声明。",
        "模型被要求只使用真实证据ID，并生成可追溯证据索引。",
        "若失败，报告引用可能无法追踪或出现虚构证据编号。",
    ),
    "tests/test_research_coverage_writer.py::test_blocked_writer_skips_llm_and_returns_safe_answer": _description(
        "验证证据覆盖率为零时跳过LLM并返回中文安全降级报告。",
        "系统记录generation_skipped和research_coverage_blocked，节省Token。",
        "若失败，阻断状态仍可能触发付费模型调用。",
    ),
    "tests/test_research_report_eval.py::test_report_dataset_is_frozen_small_and_manually_grounded": _description(
        "验证研究报告集固定为4个代表案例，且每项声明都有人工允许证据集合。",
        "评测规模适合简历项目，同时保留明确的人工证据金标准。",
        "若失败，数据可能被随意扩改或声明缺少可核验依据。",
    ),
    "tests/test_research_report_eval.py::test_grader_detects_hallucinated_citation_and_uncovered_claim": _description(
        "验证评测器能够发现不存在的Evidence ID和缺少正确邻近引用的声明。",
        "虚构引用和无证据结论都会使报告不通过。",
        "若失败，引用格式正确但内容无依据的报告可能被误判为成功。",
    ),
    "tests/test_research_report_eval.py::test_reference_reports_validate_harness_without_llm": _description(
        "验证人工参考报告只用于离线校验Harness，并明确记录零LLM调用。",
        "参考答案100%不得被误报为真实模型能力成绩。",
        "若失败，项目评测报告会混淆工具正确性与Agent实际表现。",
    ),
    "tests/test_research_report_eval.py::test_report_writer_outputs_json_and_flat_csv": _description(
        "验证一键评测同时生成完整JSON和可由Excel直接查看的CSV明细表。",
        "每个案例的引用、声明、结构和成本指标都可持续记录。",
        "若失败，评测结果无法稳定保存或进行后续版本比较。",
    ),
    "tests/test_research_report_eval.py::test_section_aliases_are_accepted_but_citations_must_be_sentence_local": _description(
        "验证合法中英文章节别名可以通过，同时引用不能跨句或跨bullet借用。",
        "结构判分避免误杀，声明覆盖判分保持严格的局部证据约束。",
        "若失败，合法报告会被误判，或无引用综合判断会借用附近引用通过。",
    ),
    "tests/test_research_report_eval.py::test_existing_paid_answers_can_be_regraded_without_llm": _description(
        "验证判分规则修复后可以复用已付费的研究报告原文重新计算指标。",
        "评测器升级不会强迫用户重复调用模型和消耗Token。",
        "若失败，任何判分修正都会增加不必要的API费用。",
    ),
    "tests/test_research_report_eval.py::test_targeted_rerun_merges_without_replacing_untouched_cases": _description(
        "验证Provider失败后可以只重跑指定案例并合并到已有完整报告。",
        "未重跑案例的模型原文、指标和Token记录保持不变。",
        "若失败，少量外部服务波动会迫使全部案例重复付费运行。",
    ),
    "tests/test_research_citation_validator.py::test_valid_grounded_report_passes_citation_validator": _description(
        "验证Evidence ID真实、综合判断同句引用且证据索引完整的研究报告通过。",
        "合规Writer输出不会被Citation Validator误阻断。",
        "若失败，正确的研究报告无法进入最终答案验证。",
    ),
    "tests/test_research_citation_validator.py::test_unknown_evidence_id_is_rejected": _description(
        "验证报告引用Evidence Store不存在的ID时记录invalid_evidence_id。",
        "虚构引用不能仅凭格式正确通过验证。",
        "若失败，读者可能收到无法定位的伪造证据编号。",
    ),
    "tests/test_research_citation_validator.py::test_uncited_synthesis_is_not_allowed_to_borrow_other_line_citation": _description(
        "验证综合判断必须在同一行引用证据，不能借用其他bullet的引用。",
        "声明级引用覆盖比章节级关键词检查更严格。",
        "若失败，无依据综合结论会被附近论文事实掩盖。",
    ),
    "tests/test_research_citation_validator.py::test_paper_critique_material_gap_is_not_paper_defect": _description(
        "验证批判报告不能把输入材料缺失写成论文贡献或实验本身的缺陷。",
        "过度审稿判断会进入critique_evidence_overreach失败类型。",
        "若失败，短摘要可能被错误用于否定完整论文质量。",
    ),
    "tests/test_research_citation_validator.py::test_non_l3_answer_keeps_validator_not_applicable": _description(
        "验证L1/L2普通回答不启用研究引用验证器。",
        "快速路径不增加新的处理成本或研究报告约束。",
        "若失败，普通问答可能因没有Evidence ID而被错误阻断。",
    ),
    "tests/test_research_citation_validator.py::test_citation_failure_enters_answer_verification_without_reflection": _description(
        "验证引用失败合并到最终答案验证，但当前阶段不会自动触发额外Reflection。",
        "失败可观测且不增加未经评测的模型调用。",
        "若失败，引用错误可能被最终Verifier忽略或造成额外Token。",
    ),
    "tests/test_research_citation_validator.py::test_paper_critique_prompt_distinguishes_material_from_paper_limitations": _description(
        "验证Paper Critique Prompt明确区分材料局限与论文真实缺陷。",
        "模型在生成前被禁止用片段缺失推断论文未做实验或无法通过审查。",
        "若失败，首轮真实基线暴露的过度批判问题可能持续出现。",
    ),
    "tests/test_citation_repair.py::test_unique_title_matches_repair_uncited_synthesis_without_llm": _description(
        "验证漏引综合判断明确出现论文标题时补全唯一对应的Evidence ID集合。",
        "可确定修复不调用LLM，并在修复后重新通过Citation Validator。",
        "若失败，简单漏引仍需重新生成整篇报告并消耗Token。",
    ),
    "tests/test_citation_repair.py::test_no_title_match_is_left_for_bounded_reflection": _description(
        "验证综合判断没有明确论文标题时保持原文，不猜测证据归属。",
        "无法唯一修复的案例留给后续受限Reflection或人工确认。",
        "若失败，系统可能自动附加不支持声明的错误引用。",
    ),
    "tests/test_citation_repair.py::test_other_citation_failures_disable_deterministic_repair": _description(
        "验证同时存在虚构Evidence ID等其他失败时禁止局部自动补全。",
        "确定性修复只处理唯一、单一的uncited_synthesis_claim。",
        "若失败，局部修复可能掩盖报告中的其他严重引用错误。",
    ),
    "tests/test_citation_repair.py::test_repair_node_updates_answer_and_validation_together": _description(
        "验证LangGraph修复节点原子更新答案、修复轨迹和重新验证结果。",
        "下游Answer Verify不会看到答案与Citation状态不一致的中间态。",
        "若失败，修复成功后仍可能沿用旧的失败判定。",
    ),
    "tests/test_citation_repair.py::test_existing_online_style_report_can_run_zero_token_ab": _description(
        "验证已有在线Writer原文可以运行零Token引用修复A/B。",
        "能力收益和成本增量可在不重复调用模型的情况下比较。",
        "若失败，无法证明自动修复相对原始报告的净效果。",
    ),
    "tests/test_deployment_config.py::test_docker_image_uses_non_root_user_and_healthcheck": _description(
        "验证Docker运行镜像使用非root用户、健康检查和统一FastAPI入口。",
        "容器以最小权限运行，并可由Docker判断服务是否健康。",
        "若失败，部署配置可能失去基本安全边界或健康探测能力。",
    ),
    "tests/test_deployment_config.py::test_dockerignore_excludes_secrets_and_large_runtime_artifacts": _description(
        "验证密钥、本地虚拟环境、模型缓存、论文PDF、会话记忆和评测产物不会进入镜像上下文。",
        "镜像保持可分享，且不会意外打包本地敏感信息和大型文件。",
        "若失败，Docker构建可能泄露配置或生成体积异常的镜像。",
    ),
    "tests/test_deployment_config.py::test_ci_is_deterministic_and_builds_the_runtime_image": _description(
        "验证基础CI清空真实模型凭据、关闭非测试LLM与Checkpoint，并检查前端语法和Docker构建。",
        "每次提交都运行稳定、零API费用的核心回归，同时允许mock覆盖LLM分支。",
        "若失败，CI可能产生外部费用、受网络波动影响或遗漏交付验证。",
    ),
    "tests/test_deployment_config.py::test_compose_persists_data_and_checks_service_health": _description(
        "验证Compose挂载数据与日志目录、为SQLite记忆使用Linux命名卷，并通过FastAPI健康端点探测服务。",
        "容器重建后项目数据仍保留，Windows环境下SQLite WAL也可稳定工作。",
        "若失败，重建容器可能丢失运行数据或无法识别启动故障。",
    ),
    "tests/test_github_mcp.py::test_github_search_uses_versioned_get_and_keeps_token_out_of_url": _description(
        "验证GitHub仓库搜索只调用固定版本的GET端点，Token仅放在请求头。",
        "搜索结果可标准化，且凭据不会进入URL、查询参数或工具结果。",
        "若失败，仓库搜索可能不稳定或在日志中泄露凭据。",
    ),
    "tests/test_github_mcp.py::test_github_inspect_normalizes_implementation_evidence": _description(
        "验证仓库检查统一整理README、目录、依赖、Issue、Release和Commit。",
        "研究报告可把论文方法与真实工程实现证据进行对照。",
        "若失败，代码侧证据可能缺失、混入Pull Request或字段格式不一致。",
    ),
    "tests/test_github_mcp.py::test_github_tools_are_registered_read_only_and_explicitly_routed": _description(
        "验证搜索与检查工具均注册为只读，并通过明确能力和github来源路由。",
        "GitHub不会自动替代论文检索，也不能绕过统一Policy和Executor。",
        "若失败，工具可能不可调用或被错误接入普通检索路径。",
    ),
    "tests/test_github_mcp.py::test_github_repository_schema_rejects_path_or_url_injection": _description(
        "验证仓库参数只接受owner/repo，不接受URL、目录穿越或额外路径。",
        "MCP Server只能访问预定义仓库端点，不能被参数改造成任意HTTP客户端。",
        "若失败，输入可能逃逸固定只读API边界。",
    ),
    "tests/test_repository_enrichment.py::test_generic_code_intent_suggests_github_without_external_call": _description(
        "验证只说代码、实现或复现时仅建议GitHub增强，不向外部服务发送内容。",
        "模糊的代码意图不会被当成用户已授权GitHub数据出站。",
        "若失败，系统可能静默把用户问题或论文信息交给第三方。",
    ),
    "tests/test_repository_enrichment.py::test_explicit_github_intent_stays_disabled_without_operator_opt_in": _description(
        "验证用户明确提到GitHub但管理员开关关闭时仍不调用外部工具。",
        "GitHub增强需要查询意图与部署配置双重授权。",
        "若失败，部署者无法统一关闭外部仓库增强。",
    ),
    "tests/test_repository_enrichment.py::test_double_opt_in_collects_repository_as_typed_evidence": _description(
        "验证双重授权后只搜索一次、检查一个仓库，并写入带GitHub定位符的repository证据。",
        "论文和工程证据可进入同一Evidence Store，同时保持类型边界与完整工具轨迹。",
        "若失败，研究报告无法可靠进行论文—代码对照或会混淆两类证据。",
    ),
    "tests/test_demo_page.py::test_demo_trace_distinguishes_repository_evidence_and_consent_state": _description(
        "验证网页展示GitHub双重授权状态，并用类型标签区分论文与代码仓库证据。",
        "简历演示可以解释是否发生数据出站、选择了哪个仓库以及证据适用边界。",
        "若失败，前端可能隐藏关键授权决策或把仓库信息误展示为论文证据。",
    ),
    "tests/test_pdf_page_analysis.py::test_selected_pdf_pages_extract_only_requested_text_and_render_png": _description(
        "验证只提取用户指定的PDF页文本，并在项目缓存目录渲染对应PNG。",
        "指定页模式不会扫描或发送整篇PDF，页面图像可供后续视觉模型使用。",
        "若失败，系统可能分析错误页面、扩大上下文或无法生成视觉输入。",
    ),
    "tests/test_pdf_page_analysis.py::test_selected_pdf_pages_reject_invalid_range_and_page_budget": _description(
        "验证超出文档范围的页码和超过3页的请求在模型调用前被拒绝。",
        "页面范围与成本预算得到确定性约束。",
        "若失败，无效页码可能造成运行错误，过多页面会放大图像Token和延迟。",
    ),
    "tests/test_pdf_page_analysis.py::test_pdf_vision_uses_separate_model_only_after_explicit_enable": _description(
        "验证显式开启页面OCR后先调用qwen3.5-ocr，再由主模型综合OCR与PDF文本。",
        "OCR提取与研究回答职责分离，两次调用、模型、页数和Token轨迹均可审计。",
        "若失败，结构化OCR原文可能直接作为最终回答，或图片被发送给错误模型。",
    ),
    "tests/test_pdf_page_analysis.py::test_pdf_vision_preserves_ocr_when_main_synthesis_fails": _description(
        "验证页面OCR成功但主模型综合失败时，系统保留已提取内容并进入可识别的降级状态。",
        "代表两阶段链路不会因第二阶段故障丢失第一阶段成果，模型与Token轨迹仍可审计。",
        "若失败，短暂的主模型故障会让已成功提取的论文页面内容一并丢失。",
    ),
    "tests/test_demo_page.py::test_demo_page_explains_selected_pdf_pages_without_exposing_local_paths": _description(
        "验证PDF冻结示例展示指定页码、图片出站状态和视觉模型，但不返回本地绝对路径。",
        "简历演示能解释文本与视觉模式的真实边界，同时保护本地文件系统信息。",
        "若失败，前端可能误报视觉能力、隐藏出站状态或暴露用户本地路径。",
    ),
    "tests/test_pdf_page_analysis.py::test_pdf_vision_smoke_requires_explicit_online_confirmation": _description(
        "验证PDF OCR在线冒烟没有confirm-online参数时在任何模型调用前退出。",
        "代表性在线测试不会在日常测试或误操作中产生图片出站与Token费用。",
        "若失败，离线回归可能意外调用百炼并发送PDF页面。",
    ),
    "tests/test_pdf_page_analysis.py::test_pdf_visual_evidence_normalizes_json_and_hides_absolute_path": _description(
        "验证OCR的JSON结果会转成统一文本，并记录来源页码、文件名和图表公式内容类型。",
        "代表多模态证据具有稳定的下游接口，同时不会把本地绝对路径暴露给模型或前端。",
        "若失败，主模型可能收到难以使用的原始JSON，或响应元数据泄露本地目录结构。",
    ),
    "tests/test_pdf_page_analysis.py::test_pdf_subskill_router_uses_explicit_intent_without_llm": _description(
        "验证PDF问题根据明确的图、表、公式关键词路由到对应子Skill，普通总结保持通用阅读。",
        "代表系统无需额外LLM调用即可选择更有针对性的分析规则，并保留低成本快速路径。",
        "若失败，公式、表格或架构图问题可能使用通用Prompt，或者普通请求被不必要地复杂化。",
    ),
    "tests/test_pdf_page_analysis.py::test_pdf_subskills_keep_grounding_and_uncertainty_rules": _description(
        "验证图、表、公式三个子Skill都保留PDF证据边界和各自的不确定性披露规则。",
        "代表专项分析不会通过猜测布局、补齐数值或套用常见符号含义来制造结论。",
        "若失败，多模态回答可能越过实际页面证据并产生看似专业但无法验证的内容。",
    ),
    "tests/test_pdf_page_analysis.py::test_pdf_grounding_validator_passes_traceable_visual_answer": _description(
        "验证标明重点页码和OCR/视觉证据模式的专项PDF回答通过Grounding检查。",
        "代表图表公式结论能够追溯到用户指定页面，并清楚披露使用了图片出站识别。",
        "若失败，合规回答会被误阻断，或系统无法确认视觉证据的使用范围。",
    ),
    "tests/test_pdf_page_analysis.py::test_pdf_grounding_validator_blocks_missing_scope_without_reflection": _description(
        "验证缺少页码、证据模式和识别不确定性的专项回答被阻断且不自动Reflection。",
        "代表确定性审计能发现失去证据边界的回答，同时不会为格式缺陷增加Token。",
        "若失败，系统可能放行无法追溯的公式解释，或进入不必要的模型修复循环。",
    ),
    "tests/test_pdf_page_analysis.py::test_pdf_grounding_validator_skips_generic_and_non_pdf_answers": _description(
        "验证通用PDF阅读和普通问答不适用专项Grounding规则。",
        "代表新增验证器只约束图表公式能力，不破坏已有快速路径和全文总结。",
        "若失败，普通回答可能被要求提供并不存在的视觉证据说明。",
    ),
    "tests/test_pdf_page_analysis.py::test_pdf_structured_contracts_reject_missing_scope_and_invalid_metric_direction": _description(
        "验证PDF结构化契约拒绝缺少证据范围和非法指标方向的结果。",
        "代表图表公式的机器可读结果必须包含可追溯页码，并使用受控枚举表达指标含义。",
        "若失败，不完整或含任意字段值的JSON可能被误当成可靠结构化结果。",
    ),
    "tests/test_pdf_page_analysis.py::test_pdf_structured_parser_returns_clean_answer_and_validated_data": _description(
        "验证合法JSON块经过Pydantic校验后写入元数据，并从用户可读答案中移除。",
        "代表同一次模型调用可以同时提供中文回答和稳定机器接口，而不会把实现JSON展示给用户。",
        "若失败，结构数据可能无法供下游使用，或网页答案混入冗长机器内容。",
    ),
    "tests/test_pdf_page_analysis.py::test_pdf_structured_parser_falls_back_without_losing_readable_answer": _description(
        "验证模型漏写JSON时记录invalid但保留正常中文回答，通用PDF阅读保持不适用。",
        "代表当前不支持原生结构化输出的主模型偶发格式失败不会中断用户任务。",
        "若失败，一次格式错误可能导致完整回答丢失，或普通PDF请求被错误标记失败。",
    ),
    "tests/test_pdf_page_analysis.py::test_pdf_structured_output_runs_through_generate_node": _description(
        "验证表格专项请求从OCR、主模型双通道输出到Pydantic校验完整贯通。",
        "代表生产Generate节点能够返回干净中文答案，同时保留可供前端和后续节点使用的指标结构。",
        "若失败，独立Schema与解析器即使通过，也可能没有真正接入LangGraph生成路径。",
    ),
    "tests/test_multi_agent_orchestrator.py::test_bounded_multi_agent_trace_composes_existing_l3_roles_without_extra_llm": _description(
        "验证L3研究任务形成Planner、Executor、Reviewer三段有序交接且不增加模型调用。",
        "代表轻量Multi-Agent复用现有研究节点，通过结构化角色轨迹展示协作而不重复生成。",
        "若失败，复杂任务可能缺少角色边界，或为了形式上的多Agent产生额外Token。",
    ),
    "tests/test_multi_agent_orchestrator.py::test_multi_agent_trace_preserves_blocked_evidence_and_review_failures": _description(
        "验证证据覆盖阻断和Reviewer失败会原样进入Multi-Agent最终状态。",
        "代表Orchestrator不会掩盖Executor或Verifier失败，也不会把降级报告标成完整成功。",
        "若失败，前端轨迹可能展示虚假的多Agent成功结论。",
    ),
    "tests/test_multi_agent_orchestrator.py::test_multi_agent_stays_off_for_fast_path_and_contract_caps_review_loop": _description(
        "验证L1快速路径不启用Multi-Agent，结构契约将Reviewer循环上限锁定为一次。",
        "代表普通问答保持低成本，复杂任务也不能演变为无限审查循环。",
        "若失败，简单请求可能承担多角色开销，或Reviewer预算约束可被绕过。",
    ),
    "tests/test_demo_page.py::test_research_conclusion_renders_markdown_as_safe_readable_html": _description(
        "验证网页把研究结论中的标题、列表、链接和表格渲染成普通AI回答样式，并先转义原始HTML。",
        "代表用户看到的是可阅读的研究结论而不是Markdown源码，同时保留基本前端注入防护。",
        "若失败，页面可能继续显示井号和列表符号，或不可信模型文本可能直接进入HTML。",
    ),
    "tests/test_comparison_retrieval.py::test_comparison_query_rewrite_preserves_both_entities_and_design_scope": _description(
        "验证GraphRAG与LightRAG比较请求改写后仍保留双方专名和核心设计约束。",
        "代表查询不会再被通用RAG规则提前截获，在线与本地检索都能看到完整意图。",
        "若失败，检索会退化为普通RAG搜索并再次触发证据不足误阻断。",
    ),
    "tests/test_comparison_retrieval.py::test_comparison_evaluator_requires_both_entities_and_explains_missing_side": _description(
        "验证比较任务只有同时获得双方证据才通过，并明确列出缺失实体。",
        "代表质量门控按任务覆盖而非中英文关键词偶然命中进行判断。",
        "若失败，单边材料可能生成虚假比较，或完整证据仍被错误阻断。",
    ),
    "tests/test_comparison_retrieval.py::test_online_comparison_uses_local_fallback_only_for_missing_entity": _description(
        "验证在线结果缺少LightRAG时只补查该实体的本地全文，并保留双来源审计。",
        "代表系统能自动组合公开发现与已有全文，不要求用户手动切换检索模式。",
        "若失败，系统可能重复检索已有一方、加载无关全文或仍无法恢复比较证据。",
    ),
    "tests/test_comparison_retrieval.py::test_missing_comparison_side_gets_targeted_single_replan": _description(
        "验证本地补充后仍缺少一方时，唯一一次Replan只搜索缺失方法的原论文与架构。",
        "代表失败恢复由明确缺口驱动，同时继续遵守最多重试一次的边界。",
        "若失败，系统会进行泛化重试、浪费调用或无法解释停止原因。",
    ),
    "tests/test_claim_evidence_validator.py::test_claim_evidence_validator_reports_supported_and_partial_claims": _description(
        "验证逐声明检查能够区分完整支持与只有部分引用匹配，并计算支持率。",
        "代表研究报告不再只检查Evidence ID存在，还能公开每条声明的最低语义支持状态。",
        "若失败，支持率会失真，或部分证据被错误当成完整支持。",
    ),
    "tests/test_claim_evidence_validator.py::test_claim_evidence_validator_blocks_insufficient_or_contradicted_claims": _description(
        "验证无关证据和明确冲突证据分别标记为insufficient与contradicted并阻断。",
        "代表引用存在但不支持结论时不会被Citation Validator的格式检查放行。",
        "若失败，模型可以用真实但无关或相反的Evidence ID包装错误声明。",
    ),
    "tests/test_claim_evidence_validator.py::test_claim_evidence_node_exposes_metrics_without_extra_llm": _description(
        "验证Claim验证节点把状态与支持率写入元数据且无需模型调用。",
        "代表服务、Metrics和前端可复用同一确定性结果，不增加Token与延迟。",
        "若失败，能力可能只存在于独立函数而未真正接入生产节点。",
    ),
    "tests/test_claim_evidence_validator.py::test_claim_evidence_failure_blocks_answer_without_reflection": _description(
        "验证证据不足的声明进入最终Answer Verifier并停止，但不自动触发额外Reflection。",
        "代表系统优先安全降级，不允许模型在没有新证据时重新措辞掩盖缺口。",
        "若失败，unsupported声明可能被放行或产生没有收益的额外模型调用。",
    ),
    "tests/test_clarification.py::test_ordinal_reference_resolves_in_range_without_llm": _description(
        "验证当前候选范围内的第二篇论文可以由序号规则直接解析且不调用模型。",
        "代表明确指代继续走低成本路径，并把解析来源记录为ordinal_rule。",
        "若失败，简单序号可能被误判、打断流程或产生不必要Token。",
    ),
    "tests/test_clarification.py::test_out_of_range_ordinal_requests_clarification_without_guessing": _description(
        "验证第10086篇等越界序号会主动澄清并记录请求序号。",
        "代表Candidate Validator能够阻止不存在的上下文对象进入检索。",
        "若失败，Agent可能猜测错误论文并生成整条错误证据链。",
    ),
    "tests/test_clarification.py::test_descriptive_reference_uses_validated_semantic_candidate": _description(
        "验证描述性指代仅在多候选时使用一次语义解析，并合并调用用量。",
        "代表复杂共指可以利用主模型理解，同时候选仍受代码验证。",
        "若失败，模糊表达无法恢复，或模型调用成本无法审计。",
    ),
    "tests/test_clarification.py::test_semantic_candidate_policy_rejects_unknown_or_low_confidence": _description(
        "验证语义解析返回的未知候选或低置信度候选不能通过代码Policy。",
        "代表LLM只有建议权，不可以创造上下文对象或绕过置信度门槛。",
        "若失败，模型幻觉候选会污染后续查询、证据和回答。",
    ),
    "tests/test_research_analysis.py::test_complexity_features_explain_l1_l2_l3_policy_decisions": _description(
        "验证research scope、比较、多目标、时间、综合和多来源特征能解释L1/L2/L3等级。",
        "代表复杂度不再只依赖少数关键词，且评分与Policy决定可在Trace中审计。",
        "若失败，自然语言复杂任务可能分级不稳，或系统无法解释升级成本。",
    ),
    "tests/test_retrieval_strategy.py::test_l2_planner_lite_splits_two_methods_then_synthesizes": _description(
        "验证L2明确比较被拆成双方独立检索和一个依赖双方证据的综合任务。",
        "代表普通比较获得针对性规划，同时不启用L3自由DAG或多轮研究成本。",
        "若失败，比较仍会使用泛化查询，或综合任务可能在缺少一方证据时提前执行。",
    ),
    "tests/test_retrieval_strategy.py::test_l2_planner_lite_uses_bounded_schedule": _description(
        "验证Planner Lite前两项最多并行2个，综合任务在第二波执行。",
        "代表L2复用零LLM Scheduler并保持明确依赖与并发边界。",
        "若失败，L2任务可能串行浪费时间或绕过依赖生成比较。",
    ),
    "tests/test_retrieval_strategy.py::test_retrieval_router_distinguishes_online_hybrid_and_unavailable_personal": _description(
        "验证统一Router区分最新在线、Local+Online混合及尚未配置的个人库请求。",
        "代表未实现的Personal Library不会伪装成功，而会记录请求范围并安全停止。",
        "若失败，检索范围可能与用户意图不一致或隐藏能力缺口。",
    ),
    "tests/test_retrieval_strategy.py::test_hybrid_strategy_merges_online_and_local_evidence": _description(
        "验证Hybrid策略将公开论文与本地全文合并为统一证据结果。",
        "代表Private Knowledge与Public Knowledge已具备当前项目级可执行接缝。",
        "若失败，Router可能只记录策略但没有真正调度两个已实现后端。",
    ),
    "tests/test_retrieval_strategy.py::test_local_scope_failure_falls_back_to_online": _description(
        "验证本地语料不可用时按策略回退在线来源而不是中断整个研究任务。",
        "代表来源失败恢复是显式、有限且可继续交付的。",
        "若失败，缺少本地模型或PDF会让本可由在线来源完成的任务直接失败。",
    ),
    "tests/test_retrieval_strategy.py::test_unavailable_personal_scope_stops_without_public_fallback": _description(
        "验证个人论文库未配置时直接停止，不用公开论文冒充用户收藏且不浪费一次Replan。",
        "代表Retrieval Scope具有诚实边界，用户明确要求的私有范围不会被静默替换。",
        "若失败，系统可能生成看似基于个人收藏、实际来自公开网络的误导性回答。",
    ),
    "tests/test_long_term_memory.py::test_memory_metadata_is_parsed_and_removed_from_user_answer": _description(
        "验证主生成调用附带的Memory Metadata可被结构化解析，并从用户可见答案中移除。",
        "代表价值判断不需要第二次LLM调用，也不会把内部控制JSON显示给用户。",
        "若失败，内部元数据可能泄露到回答，或无法进入确定性写入Policy。",
    ),
    "tests/test_long_term_memory.py::test_invalid_memory_metadata_keeps_readable_answer_and_is_rejected": _description(
        "验证模型返回损坏Metadata时仍保留正文，同时禁止长期写入。",
        "代表结构化输出异常只降级记忆能力，不会破坏本轮回答或污染数据库。",
        "若失败，格式错误可能导致答案丢失，或未验证数据被长期保存。",
    ),
    "tests/test_long_term_memory.py::test_write_gate_requires_final_verified_unchanged_answer": _description(
        "验证只有最终验证通过且生成后未被Reflection修改的答案可以写入。",
        "代表Answer/Citation/Claim验证与内容哈希共同构成写入前安全门。",
        "若失败，过期Metadata可能为已经改变或验证失败的结论授权。",
    ),
    "tests/test_long_term_memory.py::test_memory_store_writes_merges_and_versions_related_finding": _description(
        "验证新结论写入、完全重复合并、相关新版本更新三种生命周期动作。",
        "代表长期记忆不会无限复制相同结论，并保留可审计版本语义。",
        "若失败，数据库可能重复膨胀，或新结论无法替换旧版本。",
    ),
    "tests/test_long_term_memory.py::test_memory_store_skips_related_polarity_conflict": _description(
        "验证与现有结论极性相反的相关内容不会静默覆盖旧记忆。",
        "代表冲突先进入Skip与人工/后续机制处理，而不是错误自动合并。",
        "若失败，相反研究结论可能被当作普通版本更新并丢失冲突信号。",
    ),
    "tests/test_llm_usage_nodes.py::test_generate_collects_memory_metadata_in_same_llm_call": _description(
        "验证L2研究回答在主生成调用中同时返回Memory Metadata，且总调用次数仍为一次。",
        "代表长期记忆价值建议复用现有生成Token，不新增一次分类模型请求。",
        "若失败，系统可能增加额外LLM成本，或内部Metadata残留在用户答案。",
    ),
    "tests/test_long_term_memory.py::test_memory_retrieval_is_owner_isolated_and_injected_on_demand": _description(
        "验证显式历史请求只召回当前conversation owner的相关记忆并注入Skill Context。",
        "代表长期结论可以被后续研究复用，同时不同会话的数据保持隔离且不增加LLM调用。",
        "若失败，Agent可能想不起已存结论，或把其他用户/会话的私有内容混入回答。",
    ),
    "tests/test_long_term_memory.py::test_independent_l1_query_does_not_load_memory": _description(
        "验证无历史依赖的L1独立问题不会查询或注入长期研究记忆。",
        "代表Memory Need Detection能够控制上下文长度，避免每轮无差别加载历史。",
        "若失败，简单问题会承担无关上下文、延迟和潜在干扰。",
    ),
    "tests/test_long_term_memory.py::test_expired_snapshot_is_not_retrieved": _description(
        "验证超过TTL的时效性Snapshot不会重新进入研究上下文。",
        "代表最新、当前类结论不会在过期后继续冒充有效知识。",
        "若失败，Agent可能依据过时研究快照生成误导性结论。",
    ),
    "tests/test_retrieval_strategy.py::test_memory_scope_is_augmented_instead_of_reported_unavailable": _description(
        "验证基于之前结论的请求组合长期记忆与正常在线检索，而非报告Memory RAG不可用。",
        "代表派生知识提供研究上下文，公开数据源仍负责补充和验证当前论文证据。",
        "若失败，显式历史请求可能被错误中止，或只依赖旧记忆而不继续检索。",
    ),
    "tests/test_long_term_memory.py::test_conflict_is_persisted_for_owner_audit": _description(
        "验证被Write Gate阻断的相反结论会写入独立冲突审计表并进入统计。",
        "代表冲突信号不会随着单次请求结束而丢失，可供用户或后续治理流程检查。",
        "若失败，系统虽然拒绝覆盖旧结论，却无法解释或追踪候选冲突。",
    ),
    "tests/test_long_term_memory.py::test_snapshot_cleanup_marks_expired_and_preserves_audit_record": _description(
        "验证生命周期清理将到期Snapshot标记为expired而不是直接物理删除。",
        "代表过期内容不会参与召回，同时仍保留基本审计记录和状态统计。",
        "若失败，过期快照可能继续生效，或清理后完全失去可追溯性。",
    ),
    "tests/test_long_term_memory.py::test_memory_delete_is_scoped_to_owner_and_owner_delete_clears_conflicts": _description(
        "验证单条删除必须匹配Owner，整段删除同时清除该Owner的记忆与冲突。",
        "代表知道其他Owner的Memory ID也不能越权删除，并具备基础隐私清除能力。",
        "若失败，可能发生跨会话删除或用户数据删除不完整。",
    ),
    "tests/test_memory_management_api.py::test_memory_management_routes_are_registered": _description(
        "验证长期记忆查询、冲突查看、单条删除、Owner删除和过期维护路由已注册。",
        "代表生命周期能力能够通过FastAPI服务层使用，而不只存在于SQLite内部函数。",
        "若失败，管理能力无法从产品层访问或部署时路由缺失。",
    ),
    "tests/test_product_mvp.py::test_identity_register_login_and_invalid_password": _description(
        "验证注册、PBKDF2密码校验、不透明Token签发与错误密码拒绝。",
        "代表系统不保存明文密码，登录身份可以由服务端会话安全恢复。",
        "若失败，账号可能无法登录，或错误凭据被错误接受。",
    ),
    "tests/test_product_mvp.py::test_personal_library_ingests_searches_and_isolates_users": _description(
        "验证PDF按用户入库、分页切块、BM25搜索，并对另一用户返回空结果。",
        "代表Personal Library既能检索真实PDF内容，也具备数据隔离边界。",
        "若失败，个人论文无法被搜索，或不同用户的私有论文可能串库。",
    ),
    "tests/test_product_mvp.py::test_authenticated_personal_request_routes_to_private_library": _description(
        "验证已登录的我的论文请求路由至Personal Library，匿名请求明确停止。",
        "代表检索范围同时受用户意图和认证状态控制，公开来源不会冒充私人收藏。",
        "若失败，私有请求可能被路由到错误来源或匿名读取个人库。",
    ),
    "tests/test_product_mvp.py::test_retrieve_node_executes_authenticated_personal_bm25": _description(
        "验证主检索节点真实调用用户级BM25后端并返回统一论文结构。",
        "代表Personal Library不只是管理页面，已经接入LangGraph研究执行路径。",
        "若失败，Router虽选择个人库，但研究流程拿不到私人论文证据。",
    ),
    "tests/test_product_mvp.py::test_auth_and_library_api_end_to_end": _description(
        "验证注册、登录、Bearer鉴权、原始PDF上传、论文列表及匿名拒绝的API闭环。",
        "代表产品化MVP可以由前端或API客户端完整操作，而不是孤立的数据层。",
        "若失败，认证Token或论文库接口之间存在断链。",
    ),
    "tests/test_product_mvp.py::test_authenticated_hybrid_merges_personal_and_online_evidence": _description(
        "验证登录用户的Hybrid检索合并个人PDF Chunk与arXiv公开论文。",
        "代表Private Knowledge和Public Knowledge已经在同一研究请求中真实执行并统一返回。",
        "若失败，混合模式可能只显示在Router中，实际仍然只检索单一来源。",
    ),
    "tests/test_product_mvp.py::test_anonymous_api_rejects_private_retrieval_scope": _description(
        "验证匿名请求不能显式选择Personal或Hybrid私人检索范围。",
        "代表权限在LangGraph执行前由API拒绝，不会先访问私有数据再过滤。",
        "若失败，未登录客户端可能触发个人库执行路径。",
    ),
    "tests/test_demo_page.py::test_demo_page_exposes_auth_library_and_retrieval_scope_controls": _description(
        "验证网页包含注册登录、PDF论文库管理、Token请求头与四种研究范围控件。",
        "代表后端产品能力已经可以从简历演示页面完整操作。",
        "若失败，认证和个人库只能通过手写API调用，前端产品闭环不完整。",
    ),
    "tests/test_arxiv_hygiene.py::test_arxiv_withdrawn_records_are_rejected_before_ranking": _description(
        "验证标题或摘要明确声明withdrawn的arXiv记录在进入排序前被过滤。",
        "代表已撤稿候选不会占用Hybrid Top-K或作为研究结论证据。",
        "若失败，已撤回论文可能被当作正常代表工作进入Evidence Store。",
    ),
}


def catalog_key(test_file: str, test_name: str) -> str:
    """Build the stable catalog key for a JUnit testcase."""
    normalized_file = test_file.replace("\\", "/")
    base_name = test_name.split("[", 1)[0]
    return f"{normalized_file}::{base_name}"


def get_test_case_description(
    test_file: str,
    test_name: str,
) -> CaseDescription | None:
    return TEST_CASE_CATALOG.get(catalog_key(test_file, test_name))
