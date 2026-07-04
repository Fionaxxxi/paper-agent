from agent.state import AgentState
from skills.base import BaseSkill


class PaperSummarySkill(BaseSkill):
    name = "paper_summary"
    description = "论文总结 Skill"

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
    你是一个科研论文总结助手。请根据给定论文资料和历史对话，对用户问题进行结构化总结。

    【历史对话】
    {history_text}

    【论文资料】
    {documents_text}

    【用户问题】
    {query}

    请按照以下结构回答：
    1. 研究背景
    2. 研究问题
    3. 核心方法
    4. 主要贡献
    5. 实验或验证方式
    6. 局限性
    7. 简短总结

    要求：
    - 优先基于论文资料回答；
    - 不要编造资料中没有出现的内容；
    - 如果资料不足，请明确说明；
    - 回答要结构清晰，适合用于论文阅读笔记。
    """