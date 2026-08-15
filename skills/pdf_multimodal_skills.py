from agent.state import AgentState
from skills.pdf_reading_skill import PDFReadingSkill


def _grounding_instruction(state: AgentState) -> str:
    pages = state.get("pdf_selected_pages", [])
    page_text = "、".join(f"第 {page} 页" for page in pages) or "全文"
    vision_used = state.get("pdf_vision_status") == "used"
    mode = "OCR/视觉证据与提取文本" if vision_used else "仅依据提取文本或图注（未使用视觉证据）"
    return f"\n回答开头必须写明：证据范围：{page_text}；证据模式：{mode}。\n"


def _structured_instruction(schema: str) -> str:
    return f"""
在正常中文回答末尾追加一个 ```json 代码块，严格使用以下结构；不要在 JSON 中使用本地路径：
{schema}
JSON 只供程序校验，中文回答仍必须完整可读。
"""


def _schema_pages(state: AgentState) -> str:
    return str(state.get("pdf_selected_pages", [])).replace(" ", "")


class FigureUnderstandingSkill(PDFReadingSkill):
    name = "figure_understanding"
    description = "论文架构图、流程图与示意图解释 Skill"

    def build_prompt(self, state: AgentState) -> str:
        return super().build_prompt(state) + _grounding_instruction(state) + """

当前子任务是解释论文图像。请优先说明：
1. 图的目标以及输入、输出；
2. 模块、箭头和处理阶段之间的关系；
3. 图中明确出现的关键标签；
4. 图与附近 PDF 文本是否相互印证；
5. 无法辨认或仅凭图像不能确定的部分。

只有页面视觉状态为 used 时才能描述视觉位置、连线或布局；否则必须明确说明只依据图注和提取文本。
""" + _structured_instruction(
            '{"target_found":true,"summary":"...","components":["..."],"relationships":["..."],'
            f'"evidence_scope":{{"pages":{_schema_pages(state)},"evidence_mode":"text_only或ocr_visual","uncertainties":[]}}}}'
            '；若页面没有目标图，使用 target_found=false、components=[]，并在 uncertainties 说明限制'
        )


class TableAnalysisSkill(PDFReadingSkill):
    name = "table_analysis"
    description = "论文实验表格与数值比较 Skill"

    def build_prompt(self, state: AgentState) -> str:
        return super().build_prompt(state) + _grounding_instruction(state) + """

当前子任务是分析论文表格。请优先说明：
1. 表格比较对象、数据集、指标及数值方向（越高或越低越好）；
2. 关键数值、最佳结果和与基线的差异；
3. 主实验、消融或效率结果能够支持的结论；
4. 数值与附近正文是否一致；
5. 表头、单位或数值不清晰时明确标记，不得猜测或补齐。

任何“提升”结论都必须给出表格中可识别的比较对象和数值；不能只凭加粗、颜色或视觉位置推断优劣。
""" + _structured_instruction(
            '{"table_purpose":"...","metrics":[{"name":"...","direction":"higher_better或lower_better或unknown"}],'
            '"comparisons":["..."],"conclusions":["..."],'
            f'"evidence_scope":{{"pages":{_schema_pages(state)},"evidence_mode":"text_only或ocr_visual","uncertainties":[]}}}}'
        )


class FormulaExplanationSkill(PDFReadingSkill):
    name = "formula_explanation"
    description = "论文公式、损失函数与符号解释 Skill"

    def build_prompt(self, state: AgentState) -> str:
        return super().build_prompt(state) + _grounding_instruction(state) + """

当前子任务是解释论文公式。请优先说明：
1. 公式在方法中的作用；
2. 每个能够从页面或附近文本确认的符号含义；
3. 输入、输出、优化目标和计算过程；
4. 公式与算法步骤或模型模块的关系；
5. OCR 不确定、上下标含糊或正文未定义的符号。

保持原公式含义，不凭常见记号猜测本文定义；无法确认的符号必须标为未定义或识别不确定。
""" + _structured_instruction(
            '{"formula":"...","purpose":"...","symbols":[{"symbol":"...","meaning":"..."}],'
            '"computation":["..."],'
            f'"evidence_scope":{{"pages":{_schema_pages(state)},"evidence_mode":"text_only或ocr_visual","uncertainties":[]}}}}'
        )
