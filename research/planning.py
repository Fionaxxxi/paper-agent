from research.contracts import PlanValidation, ResearchAnalysis, ResearchBrief, ResearchPlan, ResearchTask

ALLOWED_SOURCES = {"arxiv", "openalex", "local_rag", "retrieval_router", "evidence_store"}


def _comparison_entities(topic: str) -> list[str]:
    import re
    match = re.search(r"(?:比较|对比)\s*(.+?)\s*(?:和|与|及|vs\.?|versus)\s*(.+?)(?:的|在|$)", topic, re.IGNORECASE)
    if not match:
        return []
    return [match.group(1).strip(), match.group(2).strip(" ？?。")]


def build_l2_planner_lite(brief: ResearchBrief) -> ResearchPlan:
    """明确比较拆成双方检索与一次综合，不构建自由DAG。"""
    entities = _comparison_entities(brief.topic)
    if len(entities) == 2:
        tasks = [
            ResearchTask(task_id="T1", objective=f"分析{entities[0]}的核心机制", query=f"{entities[0]} core architecture method original paper", source="retrieval_router", expected_evidence=f"{entities[0]}原论文方法证据"),
            ResearchTask(task_id="T2", objective=f"分析{entities[1]}的核心机制", query=f"{entities[1]} core architecture method original paper", source="retrieval_router", expected_evidence=f"{entities[1]}原论文方法证据"),
            ResearchTask(task_id="T3", objective="基于双方证据完成结构化比较", query="", source="evidence_store", depends_on=["T1", "T2"], expected_evidence="双方方法与差异的Claim–Evidence对照"),
        ]
        return ResearchPlan(objective=brief.objective, tasks=tasks, max_parallel_tasks=2)
    return build_research_plan(brief)


def build_research_brief(analysis: ResearchAnalysis) -> ResearchBrief:
    sources = ["arxiv", "openalex"] if analysis.requires_multiple_sources else ["arxiv"]
    return ResearchBrief(
        objective=f"围绕“{analysis.topic}”完成：" + "；".join(analysis.objectives),
        topic=analysis.topic,
        task_level=analysis.task_level,
        research_questions=analysis.objectives,
        evaluation_dimensions=analysis.evaluation_dimensions,
        allowed_sources=sources,
        citation_required=analysis.requires_retrieval,
    )


def build_research_plan(brief: ResearchBrief) -> ResearchPlan:
    tasks = []
    for index, question in enumerate(brief.research_questions[:4], start=1):
        tasks.append(ResearchTask(
            task_id=f"T{index}", objective=question,
            query=f"{brief.topic} {question}",
            source=brief.allowed_sources[(index - 1) % len(brief.allowed_sources)],
            expected_evidence="代表论文、方法结论与可追溯来源",
        ))
    if len(tasks) > 1 and len(tasks) < brief.max_tasks:
        tasks.append(ResearchTask(
            task_id=f"T{len(tasks) + 1}", objective="综合比较并形成研究结论",
            query="", source="evidence_store",
            depends_on=[task.task_id for task in tasks],
            expected_evidence="覆盖全部研究问题的 Claim–Evidence 对照",
        ))
    return ResearchPlan(objective=brief.objective, tasks=tasks, max_parallel_tasks=brief.max_parallel_tasks)


def validate_research_plan(plan: ResearchPlan, allowed_sources=None) -> PlanValidation:
    errors = []
    allowed = allowed_sources or ALLOWED_SOURCES
    ids = [task.task_id for task in plan.tasks]
    if len(ids) != len(set(ids)):
        errors.append("duplicate_task_id")
    objectives = [task.objective.casefold().strip() for task in plan.tasks]
    if len(objectives) != len(set(objectives)):
        errors.append("duplicate_task_objective")
    known = set(ids)
    for task in plan.tasks:
        if task.source not in allowed:
            errors.append(f"source_not_allowed:{task.task_id}:{task.source}")
        for dependency in task.depends_on:
            if dependency not in known:
                errors.append(f"unknown_dependency:{task.task_id}:{dependency}")
            if dependency == task.task_id:
                errors.append(f"self_dependency:{task.task_id}")
    edges = {task.task_id: task.depends_on for task in plan.tasks}
    visiting, visited = set(), set()
    def has_cycle(task_id):
        if task_id in visiting:
            return True
        if task_id in visited:
            return False
        visiting.add(task_id)
        if any(dep in edges and has_cycle(dep) for dep in edges[task_id]):
            return True
        visiting.remove(task_id)
        visited.add(task_id)
        return False

    if any(has_cycle(task_id) for task_id in ids):
        errors.append("cyclic_dependencies")
    return PlanValidation(valid=not errors, errors=list(dict.fromkeys(errors)))
