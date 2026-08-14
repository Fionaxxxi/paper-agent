import json

from agent.state import AgentState
from research.contracts import PaperCritiqueOutput
from skills.base import BaseSkill


class PaperCritiqueSkill(BaseSkill):
    name = "paper_critique"
    description = "从贡献、证据和可复现性角度批判性阅读论文"
    output_model = PaperCritiqueOutput

    def build_prompt(self, state: AgentState) -> str:
        context = state.get("skill_context", {})
        query = context.get("query", state.get("query", ""))
        documents_text = context.get("documents_text", state.get("documents_text", ""))
        schema = json.dumps(
            self.output_model.model_json_schema(), ensure_ascii=False, indent=2
        )
        return f"""你是严谨的论文审稿与批判性阅读助手。批评必须由提供的论文证据支持。

【用户问题】
{query}

【论文证据】
{documents_text or '暂无可用论文证据。'}

输出中文 Markdown，并覆盖下列结构化契约的全部语义字段：
{schema}

约束：
- 分开描述作者声称的贡献、可以由材料验证的优点和你的批判性判断；
- 从实验设计、基线、公平性、统计证据、外部有效性和复现条件检查弱点；
- 每项关键判断关联 URL、DOI、页码或 Chunk ID；
- 材料未覆盖的内容写“证据不足”，不得猜测。
- “输入材料没有提供某项信息”不等于“论文本身没有做这项工作”；只能写“当前材料无法验证”，禁止据此断言论文缺少实验、贡献停留在构想阶段、论文无法通过审查；
- 只有证据明确展示论文设计或实验缺陷时，才允许把它列为论文弱点，否则应列入“材料局限”而非“论文局限”。
"""
