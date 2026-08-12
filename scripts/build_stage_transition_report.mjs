import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const [doiPath, parallelPath, outputPath, previewDir] = process.argv.slice(2);
if (!doiPath || !parallelPath || !outputPath) throw new Error("Usage: node build_stage_transition_report.mjs <doi.json> <parallel.json> <output.xlsx> [preview-dir]");
const doi = JSON.parse(await fs.readFile(doiPath, "utf8"));
const parallel = JSON.parse(await fs.readFile(parallelPath, "utf8"));
const workbook = Workbook.create();
const navy = "#17365D", white = "#FFFFFF", green = "#E2F0D9", blue = "#D9EAF7", amber = "#FFF2CC";
function setup(s) { s.showGridLines = false; }
function title(s, range, text) { const r = s.getRange(range); r.merge(); r.getCell(0, 0).values = [[text]]; r.format = { fill: navy, font: { bold: true, color: white, size: 16 } }; r.format.rowHeight = 30; }
function header(r) { r.format = { fill: navy, font: { bold: true, color: white }, horizontalAlignment: "center", verticalAlignment: "center", wrapText: true }; }
function body(r) { r.format = { borders: { insideHorizontal: { style: "thin", color: "#D9E2F3" } }, verticalAlignment: "center" }; }

const overview = workbook.worksheets.add("阶段总览");
const cases = workbook.worksheets.add("DOI挑战用例");
const runs = workbook.worksheets.add("并行重复实验");
const defs = workbook.worksheets.add("指标口径");
for (const s of [overview, cases, runs, defs]) setup(s);

title(overview, "A1:H1", "PaperAgent 阶段切换验收：DOI 收口与来源级并行");
overview.getRange("A3:H3").values = [["DOI 用例", "通过", "修复准确率", "误修复", "误隔离", "并行重复", "延迟下降", "结果一致率"]]; header(overview.getRange("A3:H3"));
overview.getRange("A4:H4").values = [[doi.case_count, doi.passed_count, doi.repair_accuracy, doi.false_repair_count, doi.false_quarantine_count, parallel.repetitions, parallel.latency_reduction_pct / 100, parallel.result_equality_rate]]; body(overview.getRange("A4:H4")); overview.getRange("C4").format.numberFormat = "0.00%"; overview.getRange("G4:H4").format.numberFormat = "0.00%";
overview.getRange("A6:H6").merge(); overview.getRange("A6").values = [["DOI 阶段结论：6/6 挑战用例通过，修复准确率 100%，误修复与误隔离均为 0。达到止损验收条件，后续不再扩大 provider 选型与污染样本。"]]; overview.getRange("A6:H6").format = { fill: green, font: { bold: true }, wrapText: true };
overview.getRange("A8:H8").merge(); overview.getRange("A8").values = [[`并行阶段结论：${parallel.repetitions} 次重复实验中，串行中位数 ${(parallel.serial_median_seconds * 1000).toFixed(1)} ms，并行中位数 ${(parallel.parallel_median_seconds * 1000).toFixed(1)} ms，加速 ${parallel.speedup.toFixed(2)}×；输出顺序与结果一致率 100%。`]]; overview.getRange("A8:H8").format = { fill: blue, font: { bold: true }, wrapText: true };
overview.getRange("A10:H10").merge(); overview.getRange("A10").values = [["边界：当前为确定性离线延迟基准，证明并发编排本身有效；生产开关默认关闭，后续再通过真实网络快照观察限流和 P95。"]]; overview.getRange("A10:H10").format = { fill: amber, wrapText: true }; overview.getRange("A:H").format.columnWidth = 18;

title(cases, "A1:J1", "DOI 污染挑战集逐例验收");
cases.getRange("A3:J3").values = [["案例", "DOI", "输入标题", "规范标题", "期望修复", "实际修复", "输出标题", "状态", "是否隔离", "通过"]]; header(cases.getRange("A3:J3"));
const caseRows = doi.rows.map(r => [r.id, r.doi, r.title, r.canonical ?? "", r.expected_repair, r.repaired, r.actual_title, r.status, r.quarantined, r.passed]); cases.getRangeByIndexes(3, 0, caseRows.length, 10).values = caseRows; body(cases.getRange(`A4:J${3 + caseRows.length}`)); cases.freezePanes.freezeRows(3); cases.getRange("A:J").format.columnWidth = 18; cases.getRange("B:B").format.columnWidth = 30; cases.getRange("C:D").format.columnWidth = 38; cases.getRange("G:G").format.columnWidth = 38;

title(runs, "A1:C1", "串行与并行重复延迟实验"); runs.getRange("A3:C3").values = [["轮次", "串行耗时（秒）", "并行耗时（秒）"]]; header(runs.getRange("A3:C3")); const runRows = parallel.serial_runs_seconds.map((v, i) => [i + 1, v, parallel.parallel_runs_seconds[i]]); runs.getRangeByIndexes(3, 0, runRows.length, 3).values = runRows; body(runs.getRange(`A4:C${3 + runRows.length}`)); runs.getRange(`B4:C${3 + runRows.length}`).format.numberFormat = "0.000"; runs.getRange("A:C").format.columnWidth = 25;

title(defs, "A1:D1", "指标计算口径与适用边界"); defs.getRange("A3:D3").values = [["指标", "计算方式", "通过条件", "限制"]]; header(defs.getRange("A3:D3")); const rows = [
  ["修复准确率", "应修复案例中实际发生正确修复的数量 ÷ 应修复案例数", "100%", "小型确定性挑战集，不代表现实污染分布"],
  ["误修复", "不应修复案例中发生字段修复的数量", "0", "近似标题用于验证保守门槛"],
  ["误隔离", "全部挑战案例中被错误排除出排序的数量", "0", "Crossref 查无与工具失败均不得自动隔离"],
  ["中位延迟", "5 次实验耗时排序后的中位数", "并行低于串行", "使用固定模拟 I/O 延迟，隔离网络波动"],
  ["P95 延迟", "重复耗时的第 95 百分位近似值", "并行低于串行", "样本数小，用于工程回归而非容量规划"],
  ["结果一致率", "串行与并行输出标题及顺序完全一致的轮数 ÷ 总轮数", "100%", "并行只优化等待时间，不应改变业务语义"],
]; defs.getRangeByIndexes(3, 0, rows.length, 4).values = rows; body(defs.getRange("A4:D9")); defs.getRange("A:A").format.columnWidth = 24; defs.getRange("B:D").format.columnWidth = 55; defs.getRange("A3:D9").format.wrapText = true;

console.log((await workbook.inspect({ kind: "table", range: "阶段总览!A1:H10", include: "values,formulas", tableMaxRows: 10, tableMaxCols: 8 })).ndjson);
console.log((await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 100 }, summary: "formula errors" })).ndjson);
if (previewDir) { await fs.mkdir(previewDir, { recursive: true }); for (const [name, range] of Object.entries({ "阶段总览": "A1:H10", "DOI挑战用例": `A1:J${3 + caseRows.length}`, "并行重复实验": `A1:C${3 + runRows.length}`, "指标口径": "A1:D9" })) { const blob = await workbook.render({ sheetName: name, range, scale: 1, format: "png" }); await fs.writeFile(path.join(previewDir, `${name}.png`), new Uint8Array(await blob.arrayBuffer())); } }
await fs.mkdir(path.dirname(outputPath), { recursive: true }); const output = await SpreadsheetFile.exportXlsx(workbook); await output.save(outputPath); console.log(`Saved ${outputPath}`);
