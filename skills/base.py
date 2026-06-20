from abc import ABC
from typing import Dict, Any

from agent.state import AgentState


class BaseSkill(ABC):
    """
    所有 Skill 的基础接口。

    Skill 分为两类：
    1. LLM Skill：构造 prompt 后交给大模型生成答案
    2. Rule Skill：不调用大模型，直接基于规则生成答案
    """

    name: str = "base"
    description: str = "Base skill"
    need_llm: bool = True

    def build_prompt(self, state: AgentState) -> str:
        """
        LLM Skill 使用的方法。
        默认返回空字符串，具体 Skill 可以重写。
        """
        return ""

    def run(self, state: AgentState) -> Dict[str, Any]:
        """
        Rule Skill 使用的方法。
        默认不直接处理，由 Generate Node 调用 LLM。
        """
        return {}