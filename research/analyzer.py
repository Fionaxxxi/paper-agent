import json
import re
from langchain_openai import ChatOpenAI
from core.config import settings
from core.llm_usage import invoke_llm_with_usage
from research.contracts import ResearchAnalysis

DEEP_SIGNALS = ("前景", "价值", "趋势", "研究空白", "系统调研", "综述", "代表论文", "open problems", "future directions")
DIRECTION_SIGNALS = tuple(signal for signal in DEEP_SIGNALS if signal != "代表论文")
COMPARE_SIGNALS = ("比较", "对比", "区别", "差异", "compare", " vs ")
ALLOWED_SKILLS = {
    "qa",
    "paper_compare",
    "research_direction",
    "literature_review",
    "paper_critique",
}


class ResearchAnalysisParseError(ValueError):
    """模型已返回，但结构化结果无法解析或校验。"""

    def __init__(self, message: str, usage: dict, raw_response: str):
        super().__init__(message)
        self.usage = usage
        self.raw_response = raw_response


def build_l3_objectives(query: str, deep: list[str], compare: bool) -> list[str]:
    """从原问题构造回退目标，确保关键研究约束不会在 LLM 失败时丢失。"""
    objectives: list[str] = []
    time_match = re.search(r"20\d{2}\s*年?(?:以来|至今|以后|之后|后)", query)
    time_scope = time_match.group(0) if time_match else ""

    if any(signal in deep for signal in ("系统调研", "综述", "前景")):
        objectives.append("梳理主要研究方向")
    if "代表论文" in deep:
        objectives.append("检索代表论文")
    if any(signal in deep for signal in ("趋势", "future directions", "前景")):
        prefix = f"{time_scope}" if time_scope else ""
        objectives.append(f"分析{prefix}研究趋势与未来方向")
    if "价值" in deep:
        objectives.append("比较研究价值")
    if any(signal in deep for signal in ("研究空白", "open problems")):
        objectives.append("识别研究空白")
    if compare and not any("比较" in objective for objective in objectives):
        objectives.append("完成结构化比较")
    return list(dict.fromkeys(objectives or ["完成结构化研究分析"]))[:6]


def rule_analyze(query: str) -> ResearchAnalysis:
    lowered = query.casefold()
    deep = [signal for signal in DEEP_SIGNALS if signal in lowered]
    directions = [signal for signal in DIRECTION_SIGNALS if signal in lowered]
    compare = any(signal in lowered for signal in COMPARE_SIGNALS)
    if len(deep) >= 2 or (deep and compare):
        return ResearchAnalysis(
            intent="deep_research", task_level="L3", topic=query,
            objectives=build_l3_objectives(query, deep, compare),
            evaluation_dimensions=["成熟度", "创新空间", "工程价值", "可评测性", "未来潜力"],
            primary_skill="literature_review", secondary_skills=["research_direction", "paper_compare"],
            requires_multiple_sources=True, requires_report=True, confidence=0.72,
            reason="复杂研究信号：" + "、".join(deep),
        )
    if compare or directions:
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
    objectives = list(candidate.objectives)
    if task_level == "L3":
        for required in rule_analysis.objectives:
            constraint_terms = [
                term for term in ("趋势", "未来方向", "研究空白", "代表论文", "价值", "比较")
                if term in required
            ]
            time_scope = re.search(
                r"20\d{2}\s*年?(?:以来|至今|以后|之后|后)", required
            )
            missing_semantic = constraint_terms and not any(
                any(term in objective for term in constraint_terms)
                for objective in objectives
            )
            missing_time = bool(time_scope) and not any(
                time_scope.group(0) in objective for objective in objectives
            )
            if missing_semantic or missing_time:
                objectives.append(required)
            if len(objectives) >= 6:
                break
    return candidate.model_copy(
        update={
            "task_level": task_level,
            "primary_skill": primary_skill,
            "secondary_skills": list(dict.fromkeys(secondary_skills)),
            "objectives": objectives[:6],
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
    # 兼容 OpenAI-compatible 模型可能返回的 thinking 标签、Markdown fenced
    # JSON 或 JSON 前后解释文字。只提取首个完整对象，不用贪婪正则吞并尾部内容。
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE).strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    candidate = fenced.group(1).strip() if fenced else text
    decoder = json.JSONDecoder()
    start = candidate.find("{")
    try:
        if start < 0:
            raise ValueError("research analysis response does not contain a JSON object")
        payload, _ = decoder.raw_decode(candidate[start:])
        payload["analysis_source"] = "llm"
        return ResearchAnalysis.model_validate(payload), usage
    except Exception as error:
        raise ResearchAnalysisParseError(str(error), usage, text[:2000]) from error
