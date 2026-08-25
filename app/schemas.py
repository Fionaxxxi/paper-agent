from typing import Any, Dict, List, Optional, Literal

from pydantic import BaseModel, Field, model_validator


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
    document_id: Optional[str] = Field(
        default=None,
        description="当前用户个人论文库中的文档 ID；服务端校验 Owner 后解析 PDF",
    )
    pdf_pages: List[int] = Field(
        default_factory=list,
        description="需要重点分析的 PDF 页码，按 1 开始，最多 3 页",
        max_length=3,
    )
    retrieval_scope: Literal["auto", "online", "personal", "hybrid"] = Field(
        default="auto", description="检索范围：自动、在线、个人论文库或混合"
    )

    @model_validator(mode="after")
    def validate_pdf_page_selection(self):
        if self.pdf_path and self.document_id:
            raise ValueError("pdf_path 与 document_id 不能同时指定")
        if self.pdf_pages and not (self.pdf_path or self.document_id):
            raise ValueError("指定 pdf_pages 时必须同时提供 pdf_path 或 document_id")
        if any(isinstance(page, bool) or page < 1 for page in self.pdf_pages):
            raise ValueError("pdf_pages 必须是从 1 开始的正整数")
        return self


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(default="", max_length=80)


class LoginRequest(BaseModel):
    email: str
    password: str


class LibraryCollectionRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class LibraryDocumentUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    tags: List[str] = Field(default_factory=list, max_length=20)
    library_id: str = Field(min_length=1, max_length=80)


class ReportExportRequest(BaseModel):
    title: str = Field(default="PaperAgent 研究报告", max_length=120)
    query: str = Field(default="", max_length=4000)
    answer: str = Field(min_length=1, max_length=100000)
    task_type: str = Field(default="research", max_length=80)
    papers: List[Dict[str, Any]] = Field(default_factory=list, max_length=50)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    trace_id: str = Field(default="", max_length=120)


class PaperInfo(BaseModel):
    title: Optional[str] = None
    authors: List[str] = []
    year: Optional[int] = None
    content: Optional[str] = None
    pdf_url: Optional[str] = None
    entry_id: Optional[str] = None
    source: Optional[str] = None
    document_id: Optional[str] = None
    chunk_id: Optional[str] = None
    page: Optional[int] = None
    retrieval_score: Optional[float] = None


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
    pdf_selected_pages: List[int] = Field(default_factory=list)
    pdf_vision_status: Optional[str] = None


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
