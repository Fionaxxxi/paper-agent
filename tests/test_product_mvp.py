import pymupdf
from fastapi.testclient import TestClient

from app.api import app
from core.config import settings
from product.identity import IdentityStore
from product.personal_library import PersonalLibraryStore
from retrieval.strategy import select_retrieval_strategy
from nodes.retrieve import retrieve_by_query
import nodes.retrieve as retrieve_module


def _pdf_bytes(tmp_path, text="Agent memory supports long-term research context."):
    path = tmp_path / "paper.pdf"
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    document.save(path)
    document.close()
    return path.read_bytes()


def test_identity_register_login_and_invalid_password(tmp_path):
    store = IdentityStore(tmp_path / "product.db")
    user = store.register("Fiona@Example.com", "password-123", "Fiona")
    session = store.login("fiona@example.com", "password-123")
    assert store.authenticate(session["access_token"])["user_id"] == user["user_id"]
    try:
        store.login("fiona@example.com", "wrong-password")
        assert False, "错误密码不应登录成功"
    except ValueError:
        pass


def test_personal_library_ingests_searches_and_isolates_users(tmp_path):
    store = PersonalLibraryStore(tmp_path / "product.db", tmp_path / "files")
    created = store.ingest_pdf("u1", "agent.pdf", _pdf_bytes(tmp_path), title="Agent Memory")
    own = store.search("u1", "long-term research context")
    other = store.search("u2", "long-term research context")
    assert created["action"] == "created"
    assert own["documents"][0]["source"] == "personal_library"
    assert other["documents"] == []


def test_authenticated_personal_request_routes_to_private_library():
    authenticated = select_retrieval_strategy({"query": "根据我的论文总结 Agent Memory", "user_id": "u1"})
    anonymous = select_retrieval_strategy({"query": "根据我的论文总结 Agent Memory"})
    assert authenticated["sources"] == ["personal_library"]
    assert anonymous["mode"] == "unavailable"


def test_retrieve_node_executes_authenticated_personal_bm25(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "PRODUCT_DB_PATH", str(tmp_path / "product.db"))
    monkeypatch.setattr(settings, "PERSONAL_LIBRARY_FILES_DIR", str(tmp_path / "files"))
    PersonalLibraryStore(settings.PRODUCT_DB_PATH, settings.PERSONAL_LIBRARY_FILES_DIR).ingest_pdf(
        "u1", "agent.pdf", _pdf_bytes(tmp_path), title="Agent Memory"
    )
    result = retrieve_by_query("long-term research context", {
        "user_id": "u1",
        "retrieval_strategy": {"mode": "personal", "sources": ["personal_library"]},
    })
    assert result["retrieval_source"] == "personal_library"
    assert result["documents"][0]["title"] == "Agent Memory"
    assert result["ranking_strategy"] == "owner_scoped_bm25"


def test_authenticated_hybrid_merges_personal_and_online_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "PRODUCT_DB_PATH", str(tmp_path / "product.db"))
    monkeypatch.setattr(settings, "PERSONAL_LIBRARY_FILES_DIR", str(tmp_path / "files"))
    PersonalLibraryStore(settings.PRODUCT_DB_PATH, settings.PERSONAL_LIBRARY_FILES_DIR).ingest_pdf(
        "u1", "agent.pdf", _pdf_bytes(tmp_path), title="Private Agent Memory"
    )
    monkeypatch.setattr(retrieve_module, "retrieve_from_source", lambda query, state, source: {
        "papers": [{"title": "Public Agent Memory", "summary": "recent public evidence", "source": "arxiv", "entry_id": "online-1"}],
        "provider": source, "retrieval_source": source, "cache_hit": False,
        "tools_used": ["arxiv"], "tool_execution": {},
    })
    result = retrieve_by_query("Agent Memory long-term research context", {
        "user_id": "u1",
        "retrieval_strategy": {"mode": "hybrid", "sources": ["personal_library", "arxiv"]},
    })
    assert result["retrieval_source"] == "hybrid_personal_online"
    assert {item["source"] for item in result["documents"]} == {"personal_library", "arxiv"}


def test_anonymous_api_rejects_private_retrieval_scope():
    response = TestClient(app).post("/chat", json={"query": "总结我的论文", "retrieval_scope": "personal"})
    assert response.status_code == 401


def test_auth_and_library_api_end_to_end(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "PRODUCT_DB_PATH", str(tmp_path / "product.db"))
    monkeypatch.setattr(settings, "PERSONAL_LIBRARY_FILES_DIR", str(tmp_path / "files"))
    client = TestClient(app)
    registered = client.post("/auth/register", json={
        "email": "fiona@example.com", "password": "password-123", "display_name": "Fiona"
    })
    login = client.post("/auth/login", json={"email": "fiona@example.com", "password": "password-123"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "X-Filename": "agent.pdf", "Content-Type": "application/pdf"}
    upload = client.post("/library/documents?title=Agent%20Memory", content=_pdf_bytes(tmp_path), headers=headers)
    listed = client.get("/library/documents", headers={"Authorization": f"Bearer {token}"})
    anonymous = client.get("/library/documents")
    assert registered.status_code == 201
    assert upload.status_code == 201
    assert listed.json()["documents"][0]["title"] == "Agent Memory"
    assert anonymous.status_code == 401


def test_library_preview_endpoints_return_owned_pdf_and_searchable_chunks(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "PRODUCT_DB_PATH", str(tmp_path / "product.db"))
    monkeypatch.setattr(settings, "PERSONAL_LIBRARY_FILES_DIR", str(tmp_path / "files"))
    client = TestClient(app)
    for email in ("owner@example.com", "other@example.com"):
        client.post("/auth/register", json={
            "email": email, "password": "password-123", "display_name": email.split("@")[0]
        })
    owner_token = client.post("/auth/login", json={
        "email": "owner@example.com", "password": "password-123"
    }).json()["access_token"]
    other_token = client.post("/auth/login", json={
        "email": "other@example.com", "password": "password-123"
    }).json()["access_token"]
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    upload = client.post(
        "/library/documents?title=Agent%20Memory",
        content=_pdf_bytes(tmp_path, "Agent memory supports selective context compression."),
        headers={**owner_headers, "X-Filename": "agent-memory.pdf", "Content-Type": "application/pdf"},
    )
    document_id = upload.json()["document"]["document_id"]

    detail = client.get(f"/library/documents/{document_id}", headers=owner_headers)
    pdf = client.get(f"/library/documents/{document_id}/file", headers=owner_headers)
    preview_page = client.get(f"/library/documents/{document_id}/pages/1", headers=owner_headers)
    chunks = client.get(
        f"/library/documents/{document_id}/chunks?q=selective&page=1&page_size=12",
        headers=owner_headers,
    )
    other_headers = {"Authorization": f"Bearer {other_token}"}
    collection = client.post(
        "/library/collections", json={"name": "Agent Architecture"}, headers=owner_headers,
    )
    collection_id = collection.json()["collection"]["library_id"]
    updated = client.patch(
        f"/library/documents/{document_id}",
        json={"title": "Agent Memory Systems", "tags": ["agent", "memory"], "library_id": collection_id},
        headers=owner_headers,
    )

    assert detail.status_code == 200
    assert "storage_path" not in detail.json()["document"]
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    assert pdf.headers["content-type"].startswith("application/pdf")
    assert "inline" in pdf.headers["content-disposition"]
    assert preview_page.status_code == 200 and preview_page.content.startswith(b"\x89PNG")
    assert chunks.status_code == 200 and chunks.json()["total"] == 1
    assert "selective context compression" in chunks.json()["items"][0]["content"]
    assert collection.status_code == 201
    assert updated.json()["document"]["title"] == "Agent Memory Systems"
    assert updated.json()["document"]["metadata"]["tags"] == ["agent", "memory"]
    assert updated.json()["document"]["library_id"] == collection_id
    for suffix in ("", "/file", "/pages/1", "/chunks"):
        assert client.get(f"/library/documents/{document_id}{suffix}", headers=other_headers).status_code == 404
    assert client.patch(
        f"/library/documents/{document_id}",
        json={"title": "stolen", "tags": [], "library_id": collection_id}, headers=other_headers,
    ).status_code in {400, 404}


def test_chat_resolves_owned_document_id_without_exposing_storage_path(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "PRODUCT_DB_PATH", str(tmp_path / "product.db"))
    monkeypatch.setattr(settings, "PERSONAL_LIBRARY_FILES_DIR", str(tmp_path / "files"))
    client = TestClient(app)
    client.post("/auth/register", json={
        "email": "reader@example.com", "password": "password-123", "display_name": "Reader"
    })
    login = client.post("/auth/login", json={
        "email": "reader@example.com", "password": "password-123"
    })
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    upload = client.post(
        "/library/documents?title=GraphRAG",
        content=_pdf_bytes(tmp_path, "GraphRAG builds community summaries."),
        headers={**headers, "X-Filename": "graphrag.pdf", "Content-Type": "application/pdf"},
    )
    document_id = upload.json()["document"]["document_id"]
    captured = {}

    def fake_chat(**kwargs):
        captured.update(kwargs)
        return {
            "answer": "基于所选 GraphRAG 论文回答。", "task_type": "pdf_reading",
            "retrieval_score": 1.0, "tools_used": [], "papers": [],
            "paper_metadata": {"selected_document_id": document_id}, "node_timings": {},
            "trace_id": "trace-selected", "conversation_id": kwargs["conversation_id"],
            "pdf_path": None, "pdf_page_count": 1, "pdf_selected_pages": [1],
            "pdf_vision_status": "rendered_text_only",
        }

    monkeypatch.setattr("app.api.paper_agent_service.chat", fake_chat)
    response = client.post("/chat", headers=headers, json={
        "query": "解释这篇论文的架构图", "document_id": document_id,
        "pdf_pages": [1], "retrieval_scope": "personal",
    })

    assert response.status_code == 200
    assert captured["selected_document"] == {"document_id": document_id, "title": "GraphRAG"}
    assert captured["pdf_path"].endswith("graphrag.pdf")
    assert response.json()["data"]["pdf_path"] is None
    assert client.post("/chat", json={
        "query": "解释这篇论文", "document_id": document_id,
    }).status_code == 401
