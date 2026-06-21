from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    query: str = Field(..., description="用户输入的论文相关问题")
    conversation_id: Optional[str] = Field(
        default=None,
        description="会话 ID，用于多轮上下文记忆",
    )
    pdf_path: Optional[str] = Field(
        default=None,
        description="本地 PDF 文件路径，用于 PDF 论文阅读分析",
    )


class PaperInfo(BaseModel):
    title: Optional[str] = None
    authors: List[str] = []
    year: Optional[int] = None
    content: Optional[str] = None
    pdf_url: Optional[str] = None
    entry_id: Optional[str] = None
    source: Optional[str] = None


class ChatData(BaseModel):
    answer: str
    task_type: str
    retrieval_score: float
    tools_used: List[str]
    papers: List[PaperInfo]
    paper_metadata: Dict[str, Any]
    node_timings: Dict[str, float]
    trace_id: str
    conversation_id: str
    pdf_path: Optional[str] = None
    pdf_page_count: Optional[int] = None


class ChatResponse(BaseModel):
    success: bool
    code: str
    message: str
    data: ChatData
    trace_id: str


class ErrorResponse(BaseModel):
    success: bool
    code: str
    message: str
    trace_id: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    service: str