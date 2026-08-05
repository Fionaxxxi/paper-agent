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
        "两组结果都覆盖意图路由、查询规划、结果合并、重试路由和 LLM 用量五个模块。",
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
        "验证文档唯一键按 entry_id、PDF URL、标题的稳定优先级选择。",
        "每种可用标识生成预期键，无标识文档返回空键。",
        "同一论文可能生成不稳定键，导致重复或误合并。",
    ),
    "tests/test_result_merger.py::test_merge_documents_deduplicates_across_groups_and_preserves_priority": _description(
        "验证多查询结果跨组去重，并保留首次出现的高优先级版本。",
        "重复 entry_id 只保留 first，第二篇独立论文仍保留。",
        "合并结果可能含重复论文或被后到的低优先级数据覆盖。",
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
