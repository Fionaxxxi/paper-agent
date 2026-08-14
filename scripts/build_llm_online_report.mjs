import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const inputPath = process.argv[2] ?? "outputs/llm_online_eval/latest_llm_online.json";
const outputPath = process.argv[3] ?? "outputs/llm_online_eval/latest_llm_online.xlsx";
const previewDir = process.argv[4] ?? "outputs/llm_online_eval/previews";
const report = JSON.parse(await fs.readFile(inputPath, "utf8"));
const summary = report.summary ?? {};
const cases = report.cases ?? [];
const wb = Workbook.create();
const navy = "#17365D", blue = "#D9EAF7", green = "#E2F0D9", red = "#FCE4D6", gray = "#F2F2F2";

const overview = wb.worksheets.add("测试概览");
overview.showGridLines = false;
overview.getRange("A1:H1").merge();
overview.getRange("A1").values = [["PaperAgent 在线 LLM 能力测试报告"]];
overview.getRange("A1:H1").format = { fill: navy, font: { bold: true, color: "#FFFFFF", size: 16 }, rowHeight: 30 };
overview.getRange("A3:B10").values = [
  ["数据集", `${report.dataset_name} v${report.dataset_version}`],
  ["模型", report.model], ["运行模式", report.mode], ["Git Commit", report.git_commit],
  ["用例数", summary.case_count], ["通过数", summary.passed_count],
  ["失败数", summary.failed_count], ["通过率", (summary.pass_rate_pct ?? 0) / 100],
];
overview.getRange("D3:E7").values = [
  ["LLM 调用数", summary.llm_call_count], ["总 Token", summary.token_usage],
  ["总耗时（秒）", summary.duration_seconds], ["生成时间", report.generated_at],
  ["总体结论", summary.failed_count === 0 ? "通过" : "存在失败，需查看用例明细"],
];
overview.getRange("G3:H4").values = [
  ["Provider 失败", summary.provider_failure_count ?? 0],
  ["能力失败", summary.capability_failure_count ?? 0],
];
overview.getRange("A3:A10").format = { fill: blue, font: { bold: true } };
overview.getRange("D3:D7").format = { fill: blue, font: { bold: true } };
overview.getRange("G3:G4").format = { fill: blue, font: { bold: true } };
overview.getRange("B10").format.numberFormat = "0.0%";
overview.getRange("E6").format.numberFormat = "yyyy-mm-dd hh:mm";
overview.getRange("E7").format.fill = summary.failed_count === 0 ? green : red;
overview.getRange("A12:H12").values = [["说明", "本报告调用真实在线模型；通过代表确定性规则、结构要求和证据身份检查全部满足，不等同于人工专家对答案学术质量的最终评审。", null, null, null, null, null, null]];
overview.getRange("A12").format = { fill: gray, font: { bold: true } };
overview.getRange("B12:H12").merge(); overview.getRange("B12:H12").format.wrapText = true;
overview.getRange("A1:H12").format.verticalAlignment = "center";
overview.getRange("A:A").format.columnWidth = 18; overview.getRange("B:B").format.columnWidth = 34;
overview.getRange("C:C").format.columnWidth = 3; overview.getRange("D:D").format.columnWidth = 18;
overview.getRange("E:H").format.columnWidth = 22;

const details = wb.worksheets.add("用例明细");
details.showGridLines = false;
const headers = ["用例 ID", "类别", "测试作用", "结果", "失败类型", "耗时(秒)", "LLM调用", "Token", "失败调用", "模型错误类型", "检查项", "错误"];
const rows = cases.map(c => [
  c.id, c.category, c.description, c.passed ? "通过" : "失败", c.failure_kind ?? "", c.duration_seconds,
  c.actual?.llm_calls ?? 0, c.actual?.tokens ?? 0, c.actual?.failed_calls ?? 0,
  (c.actual?.llm_error_types ?? []).join(", "),
  Object.entries(c.checks ?? {}).map(([k,v]) => `${k}:${v ? "通过" : "失败"}`).join("；"), c.error ?? "",
]);
details.getRangeByIndexes(0, 0, 1, headers.length).values = [headers];
if (rows.length) details.getRangeByIndexes(1, 0, rows.length, headers.length).values = rows;
details.getRange("A1:L1").format = { fill: navy, font: { bold: true, color: "#FFFFFF" }, wrapText: true };
details.getRange(`A2:L${rows.length + 1}`).format.wrapText = true;
details.getRange(`A2:L${rows.length + 1}`).format.rowHeight = 48;
details.getRange(`D2:D${rows.length + 1}`).conditionalFormats.add("containsText", { text: "通过", format: { fill: green } });
details.getRange(`D2:D${rows.length + 1}`).conditionalFormats.add("containsText", { text: "失败", format: { fill: red } });
details.freezePanes.freezeRows(1);
const widths = [28, 20, 48, 12, 14, 12, 12, 12, 12, 22, 56, 36];
widths.forEach((width, i) => details.getRangeByIndexes(0, i, rows.length + 1, 1).format.columnWidth = width);

const responses = wb.worksheets.add("模型原始输出");
responses.showGridLines = false;
responses.getRange("A1:D1").values = [["用例 ID", "用户问题", "模型输出/结构化结果", "结果"]];
const responseRows = cases.map(c => [c.id, c.query, typeof c.response === "string" ? c.response : JSON.stringify(c.response, null, 2), c.passed ? "通过" : "失败"]);
if (responseRows.length) responses.getRangeByIndexes(1, 0, responseRows.length, 4).values = responseRows;
responses.getRange("A1:D1").format = { fill: navy, font: { bold: true, color: "#FFFFFF" } };
responses.getRange(`A2:D${responseRows.length + 1}`).format.wrapText = true;
// 完整原始输出仍保存在单元格中，但固定展示行高，避免长回答在
// Windows artifact runtime 中被展开为超大位图。
responses.getRange(`A2:D${responseRows.length + 1}`).format.rowHeight = 96;
responses.getRange("A:A").format.columnWidth = 28; responses.getRange("B:B").format.columnWidth = 45;
responses.getRange("C:C").format.columnWidth = 90; responses.getRange("D:D").format.columnWidth = 12;
responses.freezePanes.freezeRows(1);

await fs.mkdir(path.dirname(outputPath), { recursive: true });
await fs.mkdir(previewDir, { recursive: true });
// 预览用于版式 QA，不需要把全部长文本渲染进一张位图；工作簿本身仍
// 包含全部用例。分别抽取前几行即可验证三张工作表的视觉结构。
for (const [sheetName, range] of [
  ["测试概览", "A1:H12"],
  ["用例明细", `A1:L${Math.min(Math.max(rows.length + 1, 2), 10)}`],
  ["模型原始输出", `A1:D${Math.min(Math.max(responseRows.length + 1, 2), 4)}`],
]) {
  const preview = await wb.render({ sheetName, range, scale: 1, format: "png" });
  await fs.writeFile(path.join(previewDir, `${sheetName}.png`), new Uint8Array(await preview.arrayBuffer()));
}
const xlsx = await SpreadsheetFile.exportXlsx(wb);
await xlsx.save(outputPath);
console.log(outputPath);
