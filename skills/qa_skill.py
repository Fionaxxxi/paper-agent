from agent.state import AgentState
from skills.base import BaseSkill


class QASkill(BaseSkill):
    name = "qa"
    description = "普通论文问答 Skill"

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
    你是一个科研论文问答助手。请根据给定论文资料和历史对话，回答用户问题。

    【历史对话】
    {history_text}

    【论文资料】
    {documents_text}

    【用户问题】
    {query}

    请要求：
    1. 优先基于论文资料回答；
    2. 如果资料不足，请明确说明“当前资料不足以完全回答”；
    3. 不要编造论文中没有的信息；
    4. 回答要结构清晰、重点明确。
    """