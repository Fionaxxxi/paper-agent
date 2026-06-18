from typing import TypedDict, List, Dict, Any, Optional


class AgentState(TypedDict, total=False):
    # 用户问题
    query: str

    # 检索到的论文片段
    documents: List[Dict[str, Any]]

    # 检索质量评分
    retrieval_score: float

    # 最终答案
    answer: str

    # 工具调用记录
    tools_used: List[str]

    # token 统计，第一版先不真实统计
    token_usage: int

    # 重新检索次数
    retry_count: int

    # 论文元数据
    paper_metadata: Dict[str, Any]

    # 错误信息
    error_message: Optional[str]

    # 是否通过安全检查
    is_valid: bool

    # 错误信息
    error_message: Optional[str]

    # 改写后的检索问题
    rewritten_query: str

    # 任务类型：qa / summarize / compare / recommend
    task_type: str

    node_timings: dict