from agent.state import AgentState
from skills.base import BaseSkill


class PaperCompareSkill(BaseSkill):
    name = "paper_compare"
    description = "论文对比 Skill"

    def build_prompt(self, state: AgentState) -> str:
        query = state.get("query", "")
        documents_text = state.get("documents_text", "")
        history_text = state.get("history_text", "无历史对话。")

        return f"""
你是一个专业的科研论文对比分析助手。

用户问题：
{query}

检索到的论文内容：
{documents_text}

历史对话：
{history_text}

当前任务是：论文对比。

请对检索到的论文进行横向对比。

输出格式：

## 论文对比分析

### 1. 对比对象概述
简要说明本次对比涉及哪些论文或方法。

### 2. 核心差异对比
请从以下角度对比：
- 研究问题
- 核心方法
- 使用场景
- 优势
- 局限
- 可借鉴点

### 3. 哪些方法更适合项目改进
结合用户问题，说明哪些论文或方法更适合作为后续项目优化方向。

### 4. 总结建议
给出简短结论。

要求：
1. 必须基于检索到的论文内容
2. 不要编造论文中没有的信息
3. 如果论文信息不足，请明确说明
4. 尽量使用条目化结构
"""