from agent.state import AgentState
from skills.base import BaseSkill


class PaperCompareSkill(BaseSkill):
    name = "paper_compare"
    description = "论文对比 Skill"

    def build_prompt(self, state):
        context = state.get("skill_context", {})

        query = context.get("query", state.get("query", ""))
        history_text = context.get("history_text", state.get("history_text", "无历史对话。"))
        documents_text = context.get("documents_text", state.get("documents_text", ""))

        if not history_text:
            history_text = "无历史对话。"

        if not documents_text:
            documents_text = "暂无可用论文资料。"

        return f"""
    你是一个科研论文对比分析助手。请根据给定论文资料，比较不同论文在研究问题、方法、贡献和局限性上的差异。

    【历史对话】
    {history_text}

    【论文资料】
    {documents_text}

    【用户问题】
    {query}

    请按照以下结构回答：
    1. 对比对象概述
    2. 研究问题对比
    3. 核心方法对比
    4. 创新点与贡献对比
    5. 实验设置或评价指标对比
    6. 局限性对比
    7. 综合结论

    要求：
    - 尽量逐篇论文进行比较；
    - 不要编造论文资料中没有的信息；
    - 如果某些论文资料不足，请明确说明；
    - 可以使用表格或分点形式增强可读性。
    """