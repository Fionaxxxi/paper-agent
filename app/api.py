from fastapi import FastAPI, HTTPException

from app.schemas import ChatRequest, ChatResponse, HealthResponse
from core.logger import logger
from services.paper_agent_service import paper_agent_service


app = FastAPI(
    title="PaperAgent API",
    description="基于 LangGraph 的多 Skill 科研论文分析 Agent 系统",
    version="0.1.0",
)


@app.get("/health", response_model=HealthResponse)
def health_check():
    return {
        "status": "ok",
        "service": "PaperAgent",
    }


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    query = request.query.strip()

    if not query:
        raise HTTPException(
            status_code=400,
            detail="query 不能为空",
        )

    try:
        return paper_agent_service.chat(query)

    except Exception as e:
        logger.exception("API /chat failed: %s", e)

        raise HTTPException(
            status_code=500,
            detail=f"PaperAgent 服务执行失败：{type(e).__name__}",
        )