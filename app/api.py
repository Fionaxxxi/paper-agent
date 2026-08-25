from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from app.schemas import ChatRequest, ChatResponse, HealthResponse, LibraryCollectionRequest, LibraryDocumentUpdate, LoginRequest, RegisterRequest, ReportExportRequest
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


@app.get("/library/collections")
def list_library_collections(user=Depends(current_user)):
    return {"success": True, "collections": personal_library_store().list_libraries(user["user_id"])}


@app.post("/library/collections", status_code=201)
def create_library_collection(request: LibraryCollectionRequest, user=Depends(current_user)):
    try:
        return {"success": True, "collection": personal_library_store().create_library(user["user_id"], request.name)}
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@app.get("/library/documents/{document_id}")
def get_library_document(document_id: str, user=Depends(current_user)):
    try:
        document = personal_library_store().get_document(user["user_id"], document_id)
        return {"success": True, "document": document}
    except KeyError as error:
        raise HTTPException(status_code=404, detail="论文不存在或不属于当前用户") from error


@app.patch("/library/documents/{document_id}")
def update_library_document(document_id: str, request: LibraryDocumentUpdate, user=Depends(current_user)):
    try:
        document = personal_library_store().update_document(
            user["user_id"], document_id, title=request.title,
            tags=request.tags, library_id=request.library_id,
        )
        return {"success": True, "document": document}
    except KeyError as error:
        raise HTTPException(status_code=404, detail="论文不存在或不属于当前用户") from error
    except PermissionError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.get("/library/documents/{document_id}/file")
def preview_library_document(document_id: str, user=Depends(current_user)):
    try:
        path, filename = personal_library_store().get_document_file(user["user_id"], document_id)
        return FileResponse(
            path, media_type="application/pdf", filename=filename,
            content_disposition_type="inline",
        )
    except (KeyError, FileNotFoundError) as error:
        raise HTTPException(status_code=404, detail="论文文件不存在或不属于当前用户") from error


@app.get("/library/documents/{document_id}/pages/{page_number}")
def preview_library_document_page(document_id: str, page_number: int, user=Depends(current_user)):
    try:
        import pymupdf

        path, _ = personal_library_store().get_document_file(user["user_id"], document_id)
        with pymupdf.open(path) as document:
            if page_number < 1 or page_number > document.page_count:
                raise HTTPException(status_code=404, detail="PDF 页码不存在")
            pixmap = document[page_number - 1].get_pixmap(matrix=pymupdf.Matrix(1.45, 1.45), alpha=False)
            content = pixmap.tobytes("png")
        return Response(
            content=content, media_type="image/png",
            headers={"Cache-Control": "private, max-age=300"},
        )
    except HTTPException:
        raise
    except (KeyError, FileNotFoundError) as error:
        raise HTTPException(status_code=404, detail="论文文件不存在或不属于当前用户") from error


@app.get("/library/documents/{document_id}/chunks")
def list_library_document_chunks(
    document_id: str, page: int = 1, page_size: int = 20,
    q: str = "", user=Depends(current_user),
):
    try:
        chunks = personal_library_store().list_document_chunks(
            user["user_id"], document_id, page=page, page_size=page_size, query=q,
        )
        return {"success": True, **chunks}
    except KeyError as error:
        raise HTTPException(status_code=404, detail="论文不存在或不属于当前用户") from error


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
    pdf_path = request.pdf_path
    selected_document = None
    if request.document_id:
        if not user:
            raise HTTPException(status_code=401, detail="基于个人论文提问需要先登录")
        try:
            document = personal_library_store().get_document(user["user_id"], request.document_id)
            path, _ = personal_library_store().get_document_file(user["user_id"], request.document_id)
            pdf_path = str(path)
            selected_document = {
                "document_id": document["document_id"],
                "title": document["title"],
            }
        except (KeyError, FileNotFoundError) as error:
            raise HTTPException(status_code=404, detail="选中的论文不存在或不属于当前用户") from error

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
            pdf_path=pdf_path,
            pdf_pages=request.pdf_pages,
            retrieval_scope=request.retrieval_scope,
            selected_document=selected_document,
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
