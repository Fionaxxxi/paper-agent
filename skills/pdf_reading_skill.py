from agent.state import AgentState
from skills.base import BaseSkill


class PDFReadingSkill(BaseSkill):
    name = "pdf_reading"
    description = "PDF 论文全文阅读 Skill"
    need_llm = True

    def build_prompt(self, state: AgentState) -> str:
        query = state.get("query", "")
        pdf_text = state.get("pdf_text", "")
        pdf_path = state.get("pdf_path", "")
        pdf_page_count = state.get("pdf_page_count", 0)
        history_text = state.get("history_text", "无历史对话。")

        return f"""
你是一个专业的科研论文全文阅读助手。

历史对话：
{history_text}

用户当前问题：
{query}

PDF 文件路径：
{pdf_path}

PDF 页数：
{pdf_page_count}

PDF 提取文本：
{pdf_text}

当前任务是：PDF 论文全文阅读与分析。

请基于 PDF 提取文本回答用户问题。

如果用户要求总结论文，请按照以下结构输出：

## PDF 论文分析

### 1. 研究背景
说明论文关注的研究领域和背景。

### 2. 研究问题
说明论文主要解决什么问题。

### 3. 核心方法
总结论文提出的方法、模型或系统流程。

### 4. 实验设计
如果文本中包含实验内容，请总结数据集、对比方法和评价指标。

### 5. 主要贡献
总结论文的创新点和贡献。

### 6. 局限性
指出论文可能存在的不足。

### 7. 可改进方向
结合论文内容给出后续可以优化或扩展的方向。

要求：
1. 必须基于 PDF 文本回答
2. 不要编造 PDF 中没有的信息
3. 如果 PDF 文本不足或提取失败，需要明确说明
4. 回答要结构化
5. 如果用户问的是具体问题，则优先回答用户问题，不必机械套用全部结构
"""