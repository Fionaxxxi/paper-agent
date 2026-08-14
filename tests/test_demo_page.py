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


def test_demo_page_exposes_research_agent_trace_panels():
    """作用：演示首页包含研究计划、执行波次、Evidence和质量闸门区域。"""
    response=TestClient(app).get("/")
    for marker in ("Research Agent 工作流", "researchPlan", "schedule", "evidenceStore", "qualityGates"):
        assert marker in response.text
    assert "/static/research.css" in response.text


def test_demo_script_consumes_existing_research_metadata_contract():
    """作用：前端直接消费服务已有研究元数据，不增加新的模型或API调用。"""
    script=TestClient(app).get("/static/app.js").text
    for field in ("research_analysis", "research_plan", "research_schedule", "evidence_store", "research_coverage", "citation_validation", "citation_repair"):
        assert field in script
    assert "renderResearch(meta)" in script


def test_demo_page_offers_zero_api_frozen_research_trace():
    """作用：网络或模型不可用时仍可加载冻结L3轨迹完成简历演示。"""
    client=TestClient(app)
    assert "加载示例轨迹（零 API）" in client.get("/").text
    sample=client.get("/static/research-sample.json")
    assert sample.status_code == 200
    payload=sample.json()
    assert payload["paper_metadata"]["task_level"] == "L3"
    assert payload["paper_metadata"]["research_coverage"]["status"] == "passed"
    assert payload["paper_metadata"]["citation_validation"]["passed"] is True
