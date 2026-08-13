from fastapi.testclient import TestClient

from app.api import app
from services.paper_agent_service import PaperAgentService


def test_demo_page_is_served_from_fastapi_root():
    response=TestClient(app).get("/")
    assert response.status_code == 200
    assert "PaperAgent" in response.text
    assert "/static/app.js" in response.text


def test_paper_formatter_keeps_local_rag_evidence_fields():
    service=PaperAgentService.__new__(PaperAgentService)
    result=service.format_papers([{"title":"ReAct","content":"evidence","source":"local_rag","document_id":"react","chunk_id":"react:p9:c1","page":9,"retrieval_score":.75}])
    assert result[0]["chunk_id"] == "react:p9:c1"
    assert result[0]["page"] == 9
    assert result[0]["retrieval_score"] == .75
