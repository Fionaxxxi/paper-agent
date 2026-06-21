from agent.state import AgentState
from skills.base import BaseSkill


class PaperSummarySkill(BaseSkill):
    name = "paper_summary"
    description = "论文总结 Skill"

    def build_prompt(self, state: AgentState) -> str:
        query = state.get("query", "")
        documents_text = state.get("documents_text", "")
        history_text = state.get("history_text", "无历史对话。")

        return f"""
你是一个专业的科研论文总结助手。

用户问题：
{query}

检索到的论文内容：
{documents_text}

历史对话：
{history_text}

当前任务是：论文总结。

请对检索到的论文进行结构化总结。

输出格式：

## 论文总结

### 1. 研究背景
说明这些论文主要关注什么问题。

### 2. 核心方法
总结论文中使用的主要技术方法。

### 3. 主要贡献
总结论文的创新点和贡献。

### 4. 局限性
指出论文中可能存在的不足。

### 5. 可改进方向
结合论文内容，提出可以继续优化的方向。

要求：
1. 必须基于检索到的论文内容
2. 不要编造论文中没有的信息
3. 如果多篇论文内容差异较大，可以分点说明
4. 尽量列出相关论文标题
"""