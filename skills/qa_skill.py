from agent.state import AgentState
from skills.base import BaseSkill


class QASkill(BaseSkill):
    name = "qa"
    description = "普通论文问答 Skill"

    def build_prompt(self, state: AgentState) -> str:
        query = state.get("query", "")
        documents_text = state.get("documents_text", "")

        return f"""
你是一个专业的科研论文分析助手。

用户问题：
{query}

检索到的论文内容：
{documents_text}

请基于检索到的论文内容回答用户问题。

要求：
1. 必须基于论文内容回答
2. 不要编造论文中没有的信息
3. 如果信息不足，请明确说明
4. 尽量引用论文标题作为依据
5. 回答要清晰、简洁、有条理
"""