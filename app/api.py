from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.schemas import ChatRequest, ChatResponse, HealthResponse, LoginRequest, RegisterRequest, ReportExportRequest
from core.config import settings
from core.logger import logger
from core.trace import generate_trace_id
from errors.base import InvalidQueryError, PaperAgentError
from errors.error_codes import ErrorCode
from services.paper_agent_service import paper_agent_service
from product.runtime import identity_store, personal_library_store
from reports.exporter import export_docx, export_pdf


app = FastAPI(
    title="PaperAgent API",
    description="基于 LangGraph 的多 Skill 科研论文分析 Agent 系统",
    version="0.1.0",
)

STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
bearer = HTTPBearer(auto_error=False)


def optional_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    if not credentials:
        return None
    user = identity_store().authenticate(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="登录已失效，请重新登录")
    return user


def current_user(user=Depends(optional_user)):
    if not user:
        raise HTTPException(status_code=401, detail="该功能需要登录")
    return user


@app.get("/", include_in_schema=False)
def demo_page():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health", response_model=HealthResponse)
def health_check():
    return {
        "status": "ok",
        "service": "PaperAgent",
    }


@app.post("/auth/register", status_code=201)
def register(request: RegisterRequest):
    try:
        user = identity_store().register(request.email, request.password, request.display_name)
        library_id = personal_library_store().ensure_default_library(user["user_id"])
        return {"success": True, "user": user, "default_library_id": library_id}
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@app.post("/auth/login")
def login(request: LoginRequest):
    try:
        return {"success": True, **identity_store().login(request.email, request.password)}
    except ValueError as error:
        raise HTTPException(status_code=401, detail=str(error)) from error


@app.get("/auth/me")
def me(user=Depends(current_user)):
    return {"success": True, "user": user}


@app.post("/library/documents", status_code=201)
async def upload_library_pdf(
    request: Request,
    title: str = "",
    library_id: str = "",
    x_filename: str = Header(default="paper.pdf", alias="X-Filename"),
    user=Depends(current_user),
):
    content = await request.body()
    if len(content) > settings.PERSONAL_LIBRARY_MAX_PDF_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail="PDF 超过上传大小限制")
    try:
        document = personal_library_store().ingest_pdf(
            user["user_id"], x_filename, content, title=title, library_id=library_id
        )
        return {"success": True, "document": document}
    except (ValueError, PermissionError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.get("/library/documents")
def list_library_documents(user=Depends(current_user)):
    return {"success": True, "documents": personal_library_store().list_documents(user["user_id"])}


@app.delete("/library/documents/{document_id}")
def delete_library_document(document_id: str, user=Depends(current_user)):
    if not personal_library_store().delete_document(user["user_id"], document_id):
        raise HTTPException(status_code=404, detail="论文不存在或不属于当前用户")
    return {"success": True, "deleted": True, "document_id": document_id}


@app.post("/reports/export/{report_format}")
def export_research_report(report_format: str, request: ReportExportRequest, user=Depends(optional_user)):
    if report_format not in {"docx", "pdf"}:
        raise HTTPException(status_code=400, detail="报告格式只支持 docx 或 pdf")
    owner = user["user_id"] if user else "anonymous"
    output_dir = Path(settings.REPORT_OUTPUT_DIR) / owner
    payload = request.model_dump()
    path = export_docx(payload, output_dir) if report_format == "docx" else export_pdf(payload, output_dir)
    media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document" if report_format == "docx" else "application/pdf"
    return FileResponse(path, media_type=media_type, filename=path.name)


@app.post("/memory/maintenance/expire")
def expire_memory_snapshots(user=Depends(current_user)):
    return {"success": True, "expired_count": paper_agent_service.expire_long_term_snapshots()}


@app.get("/memory/{conversation_id}")
def list_long_term_memories(conversation_id: str, include_inactive: bool = False, user=Depends(current_user)):
    if conversation_id != user["user_id"]:
        raise HTTPException(status_code=403, detail="不能访问其他用户的长期记忆")
    return {"success": True, "data": paper_agent_service.list_long_term_memories(
        conversation_id, include_inactive=include_inactive
    )}


@app.get("/memory/{conversation_id}/conflicts")
def list_memory_conflicts(conversation_id: str, user=Depends(current_user)):
    if conversation_id != user["user_id"]:
        raise HTTPException(status_code=403, detail="不能访问其他用户的长期记忆")
    return {"success": True, "data": paper_agent_service.list_memory_conflicts(conversation_id)}


@app.delete("/memory/{conversation_id}/{memory_id}")
def delete_long_term_memory(conversation_id: str, memory_id: str, user=Depends(current_user)):
    if conversation_id != user["user_id"]:
        raise HTTPException(status_code=403, detail="不能删除其他用户的长期记忆")
    deleted = paper_agent_service.delete_long_term_memory(conversation_id, memory_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="未找到属于该会话的长期记忆")
    return {"success": True, "deleted": True, "memory_id": memory_id}


@app.delete("/memory/{conversation_id}")
def delete_owner_memory(conversation_id: str, user=Depends(current_user)):
    if conversation_id != user["user_id"]:
        raise HTTPException(status_code=403, detail="不能删除其他用户的数据")
    return {"success": True, "data": paper_agent_service.delete_owner_memory(conversation_id)}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, user=Depends(optional_user)):
    api_trace_id = generate_trace_id()
    query = request.query.strip()

    if request.retrieval_scope in {"personal", "hybrid"} and not user:
        raise HTTPException(status_code=401, detail="个人库和混合研究需要先登录")

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
            conversation_id=user["user_id"] if user else request.conversation_id,
            user_id=user["user_id"] if user else None,
            pdf_path=request.pdf_path,
            pdf_pages=request.pdf_pages,
            retrieval_scope=request.retrieval_scope,
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
