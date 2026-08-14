from research.evidence_store import build_evidence_store
from research.scheduler import build_schedule
from nodes.research_schedule import research_schedule_node
from nodes.evidence_store import evidence_store_node


def sample_plan():
    return {
        "max_parallel_tasks": 2,
        "tasks": [
            {"task_id": "T1", "objective": "梳理方法", "query": "Agent methods", "source": "arxiv", "depends_on": [], "expected_evidence": "papers"},
            {"task_id": "T2", "objective": "比较记忆", "query": "Agent memory", "source": "openalex", "depends_on": [], "expected_evidence": "papers"},
            {"task_id": "T3", "objective": "研究空白", "query": "Agent gaps", "source": "arxiv", "depends_on": [], "expected_evidence": "papers"},
            {"task_id": "T4", "objective": "综合结论", "query": "", "source": "evidence_store", "depends_on": ["T1", "T2", "T3"], "expected_evidence": "claims"},
        ],
    }


def test_scheduler_builds_bounded_dependency_waves():
    """作用：独立检索任务每批最多2个，综合任务必须在全部依赖之后。"""
    schedule = build_schedule(sample_plan())
    assert schedule["status"] == "scheduled"
    assert all(len(wave["tasks"]) <= 2 for wave in schedule["waves"])
    synthesis_wave = next(
        wave["wave"] for wave in schedule["waves"]
        if wave["tasks"][0]["task_id"] == "T4"
    )
    assert synthesis_wave == max(wave["wave"] for wave in schedule["waves"])


def test_scheduler_reports_blocked_dependencies_instead_of_looping():
    """作用：未知或循环依赖不会造成无限Agent Loop。"""
    plan = {"tasks": [{"task_id": "T1", "depends_on": ["missing"],
                       "source": "arxiv", "objective": "x", "query": "x"}]}
    result = build_schedule(plan)
    assert result["enabled"] is False
    assert result["status"] == "blocked_dependencies"


def test_evidence_store_deduplicates_and_preserves_provenance():
    """作用：同一论文证据只保存一次，同时绑定任务和可定位来源。"""
    schedule = build_schedule(sample_plan())
    document = {"title": "Agent Memory Survey", "source": "arxiv",
                "content": "Agent memory methods and research gaps", "year": 2024,
                "pdf_url": "https://arxiv.org/abs/1234.5678"}
    store = build_evidence_store(schedule, [document, dict(document)])
    assert store["evidence_count"] == 1
    assert store["evidence"][0]["locator"] == document["pdf_url"]
    assert store["evidence"][0]["task_ids"]


def test_synthesis_task_receives_claim_evidence_inputs():
    """作用：综合任务只消费依赖任务已收集的证据ID，而不是重新搜索。"""
    schedule = build_schedule(sample_plan())
    store = build_evidence_store(schedule, [{
        "title": "Agent Methods", "source": "arxiv",
        "content": "Agent methods memory gaps", "entry_id": "1",
    }])
    claim = store["claim_evidence_inputs"][0]
    assert claim["task_id"] == "T4"
    assert claim["coverage_ready"] is True
    assert claim["evidence_ids"][0].startswith("E-")


def test_non_l3_nodes_leave_fast_path_unchanged():
    """作用：普通问答不启用Scheduler或Evidence Store。"""
    scheduled = research_schedule_node({"task_level": "L1"})
    stored = evidence_store_node({"research_schedule": scheduled["research_schedule"]})
    assert scheduled["research_schedule"]["status"] == "not_applicable"
    assert stored["evidence_store"]["status"] == "not_applicable"
