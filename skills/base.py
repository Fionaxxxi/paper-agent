from abc import ABC, abstractmethod

from agent.state import AgentState


class BaseSkill(ABC):
    """
    所有 Skill 的基础接口。

    每个 Skill 负责一种具体能力，例如：
    - 论文总结
    - 论文对比
    - 研究方向推荐
    - 普通问答

    这样可以避免所有 prompt 都堆在 generate.py 里。
    """

    name: str = "base"
    description: str = "Base skill"

    @abstractmethod
    def build_prompt(self, state: AgentState) -> str:
        """
        根据 AgentState 构造当前 Skill 对应的 prompt。
        """
        pass