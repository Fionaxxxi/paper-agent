from fastapi import FastAPI, HTTPException

from app.schemas import ChatRequest, ChatResponse, HealthResponse
from core.logger import logger
from core.trace import generate_trace_id
from errors.base import InvalidQueryError, PaperAgentError
from errors.error_codes import ErrorCode
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
    api_trace_id = generate_trace_id()
    query = request.query.strip()

    if not query:
        logger.warning(
            "trace_id=%s | invalid query | query is empty",
            api_trace_id,
        )

        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "code": ErrorCode.INVALID_QUERY,
                "message": "query 不能为空",
                "trace_id": api_trace_id,
            },
        )

    try:
        data = paper_agent_service.chat(
            query=query,
            conversation_id=request.conversation_id,
            pdf_path=request.pdf_path,
        )
        trace_id = data.get("trace_id", api_trace_id)

        return {
            "success": True,
            "code": ErrorCode.SUCCESS,
            "message": "ok",
            "data": data,
            "trace_id": trace_id,
        }

    except PaperAgentError as e:
        logger.exception(
            "trace_id=%s | API /chat failed with PaperAgentError: %s",
            api_trace_id,
            e.message,
        )

        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "code": e.code,
                "message": e.message,
                "trace_id": api_trace_id,
            },
        )

    except Exception as e:
        logger.exception(
            "trace_id=%s | API /chat failed: %s",
            api_trace_id,
            e,
        )

        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "code": ErrorCode.AGENT_EXECUTION_ERROR,
                "message": f"PaperAgent 服务执行失败：{type(e).__name__}",
                "trace_id": api_trace_id,
            },
        )