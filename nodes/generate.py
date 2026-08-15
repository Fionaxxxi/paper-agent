import base64
from pathlib import Path

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from agent.state import AgentState
from core.config import settings
from core.llm_usage import (
    TrackedLLMError,
    build_llm_usage_update,
    invoke_llm_with_usage,
)
from skills.router import get_skill
from context.context_builder import attach_skill_context
from document_loader.pdf_visual_evidence import (
    build_visual_evidence,
    format_visual_evidence_for_prompt,
)
from research.writer import build_coverage_blocked_answer, build_writer_prompt
from prompts.contracts import get_prompt_version, wrap_untrusted_evidence


def get_llm(model_name: str | None = None):
    return ChatOpenAI(
        model=model_name or settings.MODEL_NAME,
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
        temperature=0,
        timeout=settings.LLM_TIMEOUT,
        max_retries=1,
    )


def truncate_text(text: str, max_length: int = settings.DOC_CONTENT_LIMIT) -> str:
    if not text:
        return ""

    if len(text) <= max_length:
        return text

    return text[:max_length] + "...[内容已截断]"


def build_pdf_multimodal_input(prompt: str, image_paths: list[str]):
    """把本地渲染页转换成兼容 OpenAI Chat 的受限多模态消息。"""
    content: list[dict] = [{"type": "text", "text": prompt}]
    for image_path in image_paths[: settings.PDF_MAX_SELECTED_PAGES]:
        path = Path(image_path)
        if not path.is_file() or path.suffix.lower() != ".png":
            continue
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded}"}})
    return [HumanMessage(content=content)] if len(content) > 1 else prompt


PDF_OCR_PROMPT = """请解析这些论文页面：提取标题、分节、正文、表格、公式、图注和可识别的布局关系。保持原文事实，不做研究结论扩写；无法识别处明确标记。"""


def build_pdf_ocr_degraded_answer(ocr_text: str, error_message: str) -> str:
    return f"""## PDF 页面 OCR 已完成，研究综合暂不可用

页面图像已经由 OCR 模型解析，但主语言模型调用失败，因此下面仅返回 OCR 提取材料，不把它扩写成研究结论。

### OCR 提取结果

{truncate_text(ocr_text, 2500)}

### 综合阶段错误

{error_message}
"""



def build_fallback_answer(state: AgentState, error_message: str = "") -> str:
    query = state.get("query", "")
    task_type = state.get("task_type", "qa")
    documents = state.get("documents", [])[: settings.MAX_GENERATE_DOCS]

    paper_lines = []

    for index, doc in enumerate(documents, start=1):
        paper_lines.append(
            f"{index}. {doc.get('title')} ({doc.get('year')})\n"
            f"   链接：{doc.get('pdf_url')}\n"
            f"   简要内容：{truncate_text(doc.get('content', ''), 300)}"
        )

    papers_text = "\n\n".join(paper_lines)

    return f"""## PaperAgent 降级回答

本次大模型生成阶段请求失败，因此先返回基于检索结果的简要分析。

### 用户问题

{query}

### 任务类型

{task_type}

### 检索到的相关论文

{papers_text}

### 初步建议

可以先根据检索到的论文，提取研究问题、核心方法和可改进点，再选择一个范围较小、可实现性较强的方向继续深入。

### 错误信息

{error_message}
"""


def build_low_quality_answer(state: AgentState) -> str:
    """Return an evidence-safe answer without spending another LLM call."""
    documents = state.get("documents", [])[: settings.MAX_GENERATE_DOCS]
    candidate_lines = [
        f"- {doc.get('title', '未命名论文')}"
        for doc in documents
    ]
    candidates = "\n".join(candidate_lines) or "- 暂无可用候选论文"
    replan = state.get("retrieval_replan", {})
    reason = replan.get("reason") or "第二轮检索质量仍低于系统门槛"

    return f"""## 证据不足，已停止继续检索

本次检索已经完成一次受控重规划，但第二轮结果仍不足以支持可靠结论。系统已达到重试预算上限，因此不会继续循环，也不会调用大模型基于低质量证据生成答案。

### 停止原因

{reason}

### 待人工核验的候选论文

{candidates}

建议缩小研究主题、补充作者/论文名/年份等限定信息，或稍后在外部论文数据源恢复后重试。
"""


def generate_node(state: AgentState) -> AgentState:
    task_type = state.get("task_type", "qa")

    if state.get("retrieval_outcome") == "stopped_low_quality":
        return {
            "answer": build_low_quality_answer(state),
            "paper_metadata": {
                **state.get("paper_metadata", {}),
                "answer_mode": "insufficient_evidence",
                "generation_skipped": True,
            },
        }

    if (
        state.get("task_level") == "L3"
        and state.get("research_coverage", {}).get("enabled")
        and not state.get("research_coverage", {}).get("writer_allowed", False)
    ):
        return {
            "answer": build_coverage_blocked_answer(state),
            "paper_metadata": {
                **state.get("paper_metadata", {}),
                "answer_mode": "research_coverage_blocked",
                "generation_skipped": True,
                "skill_used": state.get("research_analysis", {}).get("primary_skill", "qa"),
            },
        }

    if task_type != "pdf_reading" and not state.get("documents"):
        return {
            "answer": "没有检索到相关论文内容，请尝试换一个更具体的问题。"
        }

    if task_type == "pdf_reading" and not state.get("pdf_text"):
        return {
            "answer": f"PDF 文本读取失败，无法进行论文全文分析。错误信息：{state.get('pdf_error', '')}",
            "paper_metadata": {
                **state.get("paper_metadata", {}),
                "skill_used": "pdf_reading",
                "pdf_error": state.get("pdf_error", ""),
            },
        }


    vision_requested = (
        state.get("task_type") == "pdf_reading"
        and settings.PDF_VISION_ENABLED
        and bool(state.get("pdf_page_images"))
    )
    prompt_state = {**state, "pdf_vision_status": "used"} if vision_requested else state
    skill_state = attach_skill_context(prompt_state)
    skill = get_skill(skill_state)

    if not skill.need_llm:
        return skill.run(skill_state)

    prompt = skill.build_prompt(skill_state)
    is_research_writer = state.get("task_level") == "L3" and state.get(
        "research_coverage", {}
    ).get("enabled")
    if is_research_writer:
        prompt = build_writer_prompt(prompt, state)
    prompt_version = get_prompt_version(
        "research_writer" if is_research_writer else skill.name
    )

    usage_state = state
    ocr_text = ""
    visual_evidence = {}
    try:
        if vision_requested:
            ocr_input = build_pdf_multimodal_input(PDF_OCR_PROMPT, state.get("pdf_page_images", []))
            ocr_llm = get_llm(settings.PDF_VISION_MODEL_NAME)
            ocr_response, ocr_usage = invoke_llm_with_usage(
                llm=ocr_llm, prompt=ocr_input, node_name="pdf_ocr",
                model_name=settings.PDF_VISION_MODEL_NAME, prompt_version="pdf_ocr_v1",
            )
            usage_state = {**state, **build_llm_usage_update(state, ocr_usage)}
            visual_evidence = build_visual_evidence(
                str(ocr_response.content),
                pdf_path=state.get("pdf_path", ""),
                selected_pages=state.get("pdf_selected_pages", []),
                model_name=settings.PDF_VISION_MODEL_NAME,
            )
            ocr_text = visual_evidence["text"]
            ocr_evidence = wrap_untrusted_evidence(
                format_visual_evidence_for_prompt(visual_evidence),
                "PDF 页面 OCR 结果",
            )
            llm_input = f"{prompt}\n\n【页面 OCR 补充证据】\n{ocr_evidence}"
            model_name = settings.MODEL_NAME
            llm = get_llm()
        else:
            llm_input = prompt
            model_name = settings.MODEL_NAME
            llm = get_llm()
        response, usage_record = invoke_llm_with_usage(
            llm=llm,
            prompt=llm_input,
            node_name="generate",
            model_name=model_name,
            prompt_version=prompt_version,
        )
        usage_update = build_llm_usage_update(usage_state, usage_record)

        return {
            **usage_update,
            "answer": response.content,
            "pdf_vision_status": "used" if vision_requested else state.get("pdf_vision_status", "not_requested"),
            "paper_metadata": {
                **skill_state.get("paper_metadata", {}),
                "skill_used": skill.name,
                "prompt_version": prompt_version,
                "pdf_vision_model": settings.PDF_VISION_MODEL_NAME if vision_requested else "",
                "pdf_ocr_model": settings.PDF_VISION_MODEL_NAME if vision_requested else "",
                "pdf_synthesis_model": settings.MODEL_NAME if vision_requested else "",
                "pdf_visual_page_count": len(state.get("pdf_page_images", [])) if vision_requested else 0,
                "pdf_visual_evidence": visual_evidence if vision_requested else {},
            },
        }

    except TrackedLLMError as error:
        usage_update = build_llm_usage_update(
            usage_state,
            error.usage_record,
        )
        e = error.original_error
        error_message = f"{type(e).__name__}: {e}"

        return {
            **usage_update,
            "answer": build_pdf_ocr_degraded_answer(ocr_text, error_message) if vision_requested and ocr_text else build_fallback_answer(state, error_message),
            "error_message": error_message,
            "pdf_vision_status": "ocr_only_degraded" if vision_requested and ocr_text else state.get("pdf_vision_status", "failed"),
            "paper_metadata": {
                **skill_state.get("paper_metadata", {}),
                "generate_error": error_message,
                "skill_used": skill.name,
                "prompt_version": prompt_version,
                "pdf_vision_model": settings.PDF_VISION_MODEL_NAME if vision_requested else "",
                "pdf_ocr_model": settings.PDF_VISION_MODEL_NAME if vision_requested else "",
                "pdf_synthesis_model": settings.MODEL_NAME if vision_requested else "",
                "pdf_visual_page_count": len(state.get("pdf_page_images", [])) if vision_requested and ocr_text else 0,
                "pdf_visual_evidence": visual_evidence if vision_requested and ocr_text else {},
            },
        }

    except Exception as e:
        error_message = f"{type(e).__name__}: {e}"

        return {
            "answer": build_fallback_answer(state, error_message),
            "error_message": error_message,
            "paper_metadata": {
                **skill_state.get("paper_metadata", {}),
                "generate_error": error_message,
                "skill_used": skill.name,
                "prompt_version": prompt_version,
            },
        }
