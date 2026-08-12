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
