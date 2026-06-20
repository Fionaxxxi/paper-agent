from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    query: str = Field(..., description="用户输入的论文相关问题")


class PaperInfo(BaseModel):
    title: Optional[str] = None
    authors: List[str] = []
    year: Optional[int] = None
    content: Optional[str] = None
    pdf_url: Optional[str] = None
    entry_id: Optional[str] = None
    source: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    task_type: str
    retrieval_score: float
    tools_used: List[str]
    papers: List[PaperInfo]
    paper_metadata: Dict[str, Any]
    node_timings: Dict[str, float]
    trace_id: str


class HealthResponse(BaseModel):
    status: str
    service: str