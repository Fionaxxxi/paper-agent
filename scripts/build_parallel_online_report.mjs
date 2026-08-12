import fs from "node:fs/promises";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const input = process.argv[2] ?? "eval_harness/reports/parallel_retrieval_online.json";
const output = process.argv[3] ?? "outputs/parallel_online/parallel_online_report.xlsx";
const previewDir = process.argv[4] ?? "outputs/parallel_online/previews";
const report = JSON.parse(await fs.readFile(input, "utf8"));
const s = report.summary;
const wb = Workbook.create();
const navy = "#1B3B63", blue = "#DDEBF7", green = "#E2F0D9", yellow = "#FFF2CC";

function title(sheet, range, text) {
  sheet.getRange(range).merge();
  sheet.getRange(range.split(":")[0]).values = [[text]];
  sheet.getRange(range).format = { fill: navy, font: { bold: true, color: "#FFFFFF", size: 16 }, rowHeight: 28 };
  sheet.showGridLines = false;
}
function header(range) {
  range.format = { fill: navy, font: { bold: true, color: "#FFFFFF" }, horizontalAlignment: "center", borders: { preset: "inside", style: "thin", color: "#FFFFFF" } };
}

const overview = wb.worksheets.add("阶段总览");
title(overview, "A1:H1", "PaperAgent 在线并行 A/B 与阶段切换");
overview.getRange("A3:H3").values = [["串行 P50(s)", "并行 P50(s)", "延迟下降", "结果重合", "工具失败", "限流", "晋升", "下一阶段"]];
header(overview.getRange("A3:H3"));
overview.getRange("A4:H4").values = [[s.serial_p50_seconds, s.parallel_p50_seconds, s.latency_reduction_pct / 100, s.mean_result_overlap_rate, s.failure_count, s.rate_limited_count, s.acceptance_passed ? "通过" : "不通过", "子查询有界并行"]];
overview.getRange("A4:D4").format.numberFormat = [["0.000", "0.000", "0.0%", "0.0%"]];
overview.getRange("A6:H6").merge();
overview.getRange("A6").values = [["结论：单次真实网络试跑中并行延迟较低，但 arXiv 请求失败，晋升门槛不通过；生产开关保持关闭，不再重复施压外部 API。"]];
overview.getRange("A6:H6").format = { fill: yellow, font: { bold: true }, wrapText: true, rowHeight: 34 };
overview.getRange("A8:H8").merge();
overview.getRange("A8").values = [["下一阶段：已实现子查询级独立开关、最多 2 个 worker、按规划顺序收集；接下来补离线重复基准后进入 Retrieval Replan。"]];
overview.getRange("A8:H8").format = { fill: blue, font: { bold: true }, wrapText: true, rowHeight: 34 };
overview.getRange("A:H").format.columnWidth = 18;

const runs = wb.worksheets.add("在线原始记录");
title(runs, "A1:J1", "真实网络串行与并行原始记录");
runs.getRange("A3:J3").values = [["轮次", "查询", "模式", "耗时(s)", "论文数", "来源", "失败码", "结果重合", "是否有效", "说明"]];
header(runs.getRange("A3:J3"));
const rows = report.runs.map(r => [r.repetition, r.query, r.mode, r.latency_seconds, r.paper_count, r.providers.join(", "), r.failure_codes.join(", "), r.pair_overlap_rate, r.failure_codes.length === 0, r.failure_codes.length ? "外部工具失败，不能用于晋升" : "有效请求"]);
if (rows.length) runs.getRangeByIndexes(3, 0, rows.length, 10).values = rows;
runs.getRange(`D4:D${3 + rows.length}`).format.numberFormat = "0.000";
runs.getRange(`H4:H${3 + rows.length}`).format.numberFormat = "0.0%";
runs.getRange("A:J").format.columnWidth = 18;
runs.getRange("B:B").format.columnWidth = 42;
runs.getRange("J:J").format.columnWidth = 30;
runs.freezePanes.freezeRows(3);

const rules = wb.worksheets.add("门槛与口径");
title(rules, "A1:D1", "晋升门槛与指标口径");
rules.getRange("A3:D3").values = [["指标", "计算方法", "通过条件", "本次结论"]];
header(rules.getRange("A3:D3"));
rules.getRange("A4:D8").values = [
  ["P50 延迟", "同模式耗时的中位数", "观察项", `${s.serial_p50_seconds}s → ${s.parallel_p50_seconds}s`],
  ["P95 延迟", "排序后第 95 百分位近似值", "并行不高于串行", s.parallel_p95_seconds <= s.serial_p95_seconds ? "通过" : "失败"],
  ["结果重合率", "串并行结果身份集合交并比的平均值", ">=95%", `${(s.mean_result_overlap_rate * 100).toFixed(1)}%`],
  ["工具失败", "tool_success=false 的执行数", "必须为 0", `${s.failure_count}`],
  ["总门槛", "上述质量、延迟、失败条件同时满足", "全部满足", s.acceptance_passed ? "通过" : "不通过"],
];
rules.getRange("A4:D8").format = { wrapText: true, borders: { preset: "inside", style: "thin", color: "#D9E2F3" } };
rules.getRange("A:D").format.columnWidth = 30;
rules.getRange("B:B").format.columnWidth = 46;
rules.getRange("A10:D10").merge();
rules.getRange("A10").values = [["边界：本次仅 1 个查询、每种模式 1 次，且外部 API 失败；数据只验证评测门槛，不代表稳定网络性能。"]];
rules.getRange("A10:D10").format = { fill: yellow, wrapText: true, rowHeight: 34 };

for (const sheetName of ["阶段总览", "在线原始记录", "门槛与口径"]) {
  const sheet = wb.worksheets.getItem(sheetName);
  const used = sheet.getUsedRange();
  used.format.font = { name: "Microsoft YaHei" };
}

await fs.mkdir(previewDir, { recursive: true });
for (const sheetName of ["阶段总览", "在线原始记录", "门槛与口径"]) {
  const png = await wb.render({ sheetName, autoCrop: "all", scale: 1, format: "png" });
  await fs.writeFile(`${previewDir}/${sheetName}.png`, new Uint8Array(await png.arrayBuffer()));
}
console.log((await wb.inspect({ kind: "table", range: "阶段总览!A1:H8", include: "values,formulas", tableMaxRows: 10, tableMaxCols: 10 })).ndjson);
console.log((await wb.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 100 } })).ndjson);
await fs.mkdir(output.split(/[\\/]/).slice(0, -1).join("/"), { recursive: true });
const xlsx = await SpreadsheetFile.exportXlsx(wb);
await xlsx.save(output);
console.log(output);
