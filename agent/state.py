from typing import TypedDict, List, Dict, Any, Optional


class AgentState(TypedDict, total=False):
    # 用户问题
    query: str

    input_intent: str

    # 检索到的论文片段
    documents: List[Dict[str, Any]]

    # 检索质量评分
    retrieval_score: float
    retrieval_outcome: str
    retrieval_stop_reason: str

    # 最终答案
    answer: str

    # 工具调用记录
    tools_used: List[str]

    # LLM 调用与 token 统计
    token_usage: int
    input_token_usage: int
    output_token_usage: int
    llm_call_count: int
    llm_failed_call_count: int
    llm_usage: List[Dict[str, Any]]

    # 重新检索次数
    retry_count: int
    retry_query: str
    retrieval_replan: Dict[str, Any]

    # 论文元数据
    paper_metadata: Dict[str, Any]

    # 错误信息
    error_message: Optional[str]

    # 是否通过安全检查
    is_valid: bool

    # 改写后的检索问题
    rewritten_query: str

    # 任务类型：qa / summarize / compare / recommend
    task_type: str

    node_timings: dict

    trace_id: str

    conversation_id: str
    history: List[Dict[str, Any]]
    history_text: str

    pdf_path: str
    pdf_text: str
    pdf_page_count: int
    pdf_error: str

    sub_queries: list[str]
    query_plan_enabled: bool
    query_plan_reason: str
    query_complexity: str
    complexity_reason: str

    # query_rewrite.py 增加 rewritten_query
    # retrieve.py 增加 documents
    # evaluate.py 增加 retrieval_score
    # reason.py 增加 task_type
    # generate.py 增加 answer
    # metrics.py 增加 metrics
