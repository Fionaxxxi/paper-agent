# PDF 视觉理解 v2 阶段报告

## 本轮目标

将 PDF 能力从“用户指定页码后的 OCR 补充”升级为研究型 Agent 可使用的关键页视觉分析，同时继续限制图片出站、Token 和循环预算。

## 已完成能力

1. 自动关键页选择：用户未填写页码但明确询问架构图、实验表、曲线图或公式时，系统在本地按查询词、Figure/Table/Algorithm 标记和图注打分，最多选择 3 页；普通全文总结不触发。
2. 查询感知视觉解析：视觉模型同时收到用户问题、页码和专项任务，不再只做无差别文字转录。
3. Chart Analysis Skill：新增曲线、柱状、散点、热力、面积和箱线图分析，重点检查坐标轴、系列、趋势、拐点、误差带与不可辨认项。
4. 四类结构化视觉结果：Figure、Table、Chart、Formula 都使用 Pydantic 契约记录页码、证据模式和不确定性，机器 JSON 不直接展示给用户。
5. Visual Evidence v2：记录分析模式、视觉任务、页面选择依据、内容类型和模型；只公开文件名，不公开本地绝对路径。
6. 前端可观测性：展示自动/手动选页、视觉任务、证据类型、图片出站、模型、结构化契约和 Grounding 状态。

## 成本与安全边界

- 自动选页为本地确定性逻辑，0 LLM、0 Token。
- 只在明确视觉意图下自动选页，最多 3 页；页面文本扫描上限为 120 页。
- `PDF_VISION_ENABLED=false` 时图片不出站，专项 Skill 只能依据提取文本和图注回答。
- 开启视觉后为两阶段受限调用：`qwen3.5-ocr` 解析关键页，主模型结合页面文本综合。
- 模糊刻度、颜色、上下标或连线必须写入不确定项，不允许补齐或猜测。

## 测试结果

| 测试范围 | 结果 | 调用 LLM | 说明 |
|---|---:|---:|---|
| PDF v2 专项 + 前端 + Prompt | 35/35 通过 | 0 | 自动选页、四类 Skill、Schema、Grounding、展示与版本契约 |
| 项目完整离线回归 | 422/422 通过 | 0 | LangGraph、Tool/MCP、RAG、记忆、认证、报告、Docker/CI 等全部回归 |
| 真实在线视觉冒烟 | 未完成 | 0 Token | 沙箱网络失败；外网重试要求用户明确授权指定 PDF 第 4 页出站 |

完整测试表：`outputs/test_reports/full_pdf_visual_v2/latest_test_details.csv`。

## 当前边界

- 当前自动选择的是页面，不裁剪单个 Figure/Table 区域。
- 主模型消费视觉模型产生的结构化页面证据，没有再次接收原始图片。
- 尚未实现跨页图表拼接、跨论文曲线对齐和 Visual Evidence 向量检索。
- 这些能力只有在真实案例证明必要时再增加，当前版本已经足够展示“研究型 Agent 会读关键论文图表”的主线。

## 真实在线复测

明确同意将代表性 GraphRAG 论文第 4 页发送给百炼后运行：

```powershell
D:\miniconda3\envs\paper_agent\python.exe -m eval_harness.pdf_vision_smoke --confirm-online
```

结果写入 `outputs/pdf_vision_smoke/latest.json`，不保存 API Key、Base64 图片或本地绝对路径。
