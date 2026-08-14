import json
import re
from langchain_openai import ChatOpenAI
from core.config import settings
from core.llm_usage import invoke_llm_with_usage
from research.contracts import ResearchAnalysis

DEEP_SIGNALS = ("前景", "价值", "趋势", "研究空白", "系统调研", "综述", "代表论文", "open problems", "future directions")
COMPARE_SIGNALS = ("比较", "对比", "区别", "差异", "compare", " vs ")
ALLOWED_SKILLS = {
    "qa",
    "paper_compare",
    "research_direction",
    "literature_review",
    "paper_critique",
}


def rule_analyze(query: str) -> ResearchAnalysis:
    lowered = query.casefold()
    deep = [signal for signal in DEEP_SIGNALS if signal in lowered]
    compare = any(signal in lowered for signal in COMPARE_SIGNALS)
    if len(deep) >= 2 or (deep and compare):
        return ResearchAnalysis(
            intent="deep_research", task_level="L3", topic=query,
            objectives=["梳理主要方向", "检索代表论文", "比较研究价值", "识别研究空白"],
            evaluation_dimensions=["成熟度", "创新空间", "工程价值", "可评测性", "未来潜力"],
            primary_skill="literature_review", secondary_skills=["research_direction", "paper_compare"],
            requires_multiple_sources=True, requires_report=True, confidence=0.72,
            reason="复杂研究信号：" + "、".join(deep),
        )
    if compare or deep:
        return ResearchAnalysis(
            intent="research_comparison" if compare else "research_direction",
            task_level="L2", topic=query,
            objectives=["检索相关论文", "完成结构化比较" if compare else "总结研究方向"],
            primary_skill="paper_compare" if compare else "research_direction",
            confidence=0.85, reason="规则识别到比较或方向分析任务",
        )
    return ResearchAnalysis(
        intent="paper_search" if any(word in lowered for word in ("检索", "搜索", "论文", "paper")) else "research_qa",
        task_level="L1", topic=query, objectives=["检索并回答用户的单一研究问题"],
        confidence=0.95, reason="单一明确研究目标",
    )


def should_use_llm(analysis):
    return analysis.task_level == "L3" and analysis.confidence < 0.8


def enforce_analysis_policy(
    rule_analysis: ResearchAnalysis,
    candidate: ResearchAnalysis,
) -> ResearchAnalysis:
    """LLM 负责理解，代码负责等级、Skill 和成本边界。"""

    task_level = candidate.task_level
    if rule_analysis.task_level == "L3" and candidate.task_level != "L3":
        task_level = "L3"
    primary_skill = candidate.primary_skill
    if primary_skill not in ALLOWED_SKILLS:
        primary_skill = "literature_review" if task_level == "L3" else "qa"
    secondary_skills = [
        skill for skill in candidate.secondary_skills if skill in ALLOWED_SKILLS
    ]
    return candidate.model_copy(
        update={
            "task_level": task_level,
            "primary_skill": primary_skill,
            "secondary_skills": list(dict.fromkeys(secondary_skills)),
            "requires_retrieval": True,
            "requires_report": task_level == "L3" or candidate.requires_report,
        }
    )


def analyze_with_llm(query):
    llm = ChatOpenAI(model=settings.MODEL_NAME, api_key=settings.OPENAI_API_KEY,
                     base_url=settings.OPENAI_BASE_URL, temperature=0,
                     timeout=settings.LLM_TIMEOUT, max_retries=1)
    prompt = f"""将用户研究请求转换为严格 JSON，不要输出额外文字。
字段：intent, task_level(L1/L2/L3), topic, objectives(1-6), evaluation_dimensions,
source_requirements, primary_skill, secondary_skills, requires_retrieval,
requires_multiple_sources, requires_report, confidence, reason。
用户请求：{query}"""
    response, usage = invoke_llm_with_usage(llm, prompt, "research_analyze", settings.MODEL_NAME)
    text = response.content.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    payload = json.loads(fenced.group(1) if fenced else text)
    payload["analysis_source"] = "llm"
    return ResearchAnalysis.model_validate(payload), usage
