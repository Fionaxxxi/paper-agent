from agent.state import AgentState
from skills.base import BaseSkill


class ResearchDirectionSkill(BaseSkill):
    name = "research_direction"
    description = "研究方向推荐 Skill"

    def build_prompt(self, state: AgentState) -> str:
        query = state.get("query", "")
        documents_text = state.get("documents_text", "")

        return f"""
你是一个科研选题与论文分析助手。

用户问题：
{query}

检索到的论文内容：
{documents_text}

当前任务是：研究方向推荐。

请基于检索到的论文，为用户推荐适合继续研究或做项目的方向。

输出格式：

## 研究方向推荐

### 1. 检索论文覆盖的主要方向
先总结这些论文大致覆盖了哪些研究主题。

### 2. 推荐研究方向
给出 3 个适合切入的研究方向。

每个方向包含：
- 方向名称
- 可借鉴论文
- 为什么适合作为选题
- 可以怎么改进
- 实现难度
- 预期成果形式

### 3. 优先级排序
按照“可实现性 + 创新性 + 展示效果”给出排序。

### 4. 最终建议
给出最推荐的一个方向，并说明原因。

要求：
1. 不要使用“必发”“一定出成果”等绝对化表达
2. 必须基于检索到的论文内容
3. 如果论文信息不足，需要说明
4. 建议要具体，不能只说大方向
"""