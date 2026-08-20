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
