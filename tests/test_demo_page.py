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


def test_demo_trace_distinguishes_repository_evidence_and_consent_state():
    """作用：网页明确展示GitHub双重授权状态，并区分论文与代码仓库证据。"""
    client = TestClient(app)
    page = client.get("/").text
    script = client.get("/static/app.js").text
    sample = client.get("/static/research-sample.json").json()

    assert "GitHub 代码证据" in page
    assert "repository_enrichment" in script
    assert "没有向 GitHub 发送查询" in script
    assert sample["paper_metadata"]["repository_enrichment"]["status"] == "collected"
    evidence_types = {item["evidence_type"] for item in sample["paper_metadata"]["evidence_store"]["evidence"]}
    assert evidence_types == {"paper", "repository"}


def test_demo_page_explains_selected_pdf_pages_without_exposing_local_paths():
    """作用：PDF冻结示例展示页码、视觉出站状态和模型，但不包含本地路径。"""
    client = TestClient(app)
    page = client.get("/").text
    script = client.get("/static/app.js").text
    sample_response = client.get("/static/pdf-page-sample.json")

    assert "加载PDF页示例（零 API）" in page
    assert "指定 PDF 页面分析" in page
    assert "图片出站" in script
    assert sample_response.status_code == 200
    sample = sample_response.json()
    assert sample["pdf_selected_pages"] == [3]
    assert sample["pdf_vision_status"] == "used"
    assert sample["paper_metadata"]["pdf_vision_model"] == "qwen3-vl-flash"
    assert "D:\\" not in sample_response.text
