import json

from agent.state import AgentState
from research.contracts import LiteratureReviewOutput
from skills.base import BaseSkill


class LiteratureReviewSkill(BaseSkill):
    name = "literature_review"
    description = "基于多篇可追溯证据生成结构化中文文献综述"
    output_model = LiteratureReviewOutput

    def build_prompt(self, state: AgentState) -> str:
        context = state.get("skill_context", {})
        query = context.get("query", state.get("query", ""))
        documents_text = context.get("documents_text", state.get("documents_text", ""))
        brief = state.get("research_brief", {})
        schema = json.dumps(
            self.output_model.model_json_schema(), ensure_ascii=False, indent=2
        )
        return f"""你是严谨的学术文献综述助手。只能根据提供的论文证据形成结论。

【研究问题】
{query}

【Research Brief】
{json.dumps(brief, ensure_ascii=False)}

【论文证据】
{documents_text or '暂无可用论文证据。'}

先在内部按研究主题、方法、证据、局限和研究空白组织材料，然后输出中文 Markdown。
必须覆盖 JSON Schema 中的全部语义字段，但最终展示为易读的中文标题和列表：
{schema}

约束：
- 每个重要结论都应关联论文标题及 URL、DOI、页码或 Chunk ID；
- 区分论文明确结论与基于多篇材料做出的综合判断；
- 不得把未提供的信息写成事实；证据不足时明确标记；
- 不以论文数量代替证据质量，不虚构研究趋势或实验结果。
"""
