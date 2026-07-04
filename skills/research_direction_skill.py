from agent.state import AgentState
from skills.base import BaseSkill


class ResearchDirectionSkill(BaseSkill):
    name = "research_direction"
    description = "研究方向推荐 Skill"

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
    你是一个科研选题与研究方向分析助手。请根据给定论文资料和历史对话，为用户推荐可继续深入的研究方向。

    【历史对话】
    {history_text}

    【论文资料】
    {documents_text}

    【用户问题】
    {query}

    请按照以下结构回答：
    1. 当前研究现状简述
    2. 可选研究方向列表
    3. 每个方向的提出依据
    4. 可行的改进思路
    5. 可能使用的数据集或评价指标
    6. 实验设计建议
    7. 推荐优先级

    要求：
    - 研究方向必须尽量基于论文资料；
    - 不要空泛地罗列方向，要说明为什么值得做；
    - 如果资料不足，请明确说明；
    - 优先推荐适合个人项目或课程项目落地的方向。
    """