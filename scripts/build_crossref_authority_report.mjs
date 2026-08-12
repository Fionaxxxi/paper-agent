import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const [inputPath, outputPath, previewDir] = process.argv.slice(2);
if (!inputPath || !outputPath) throw new Error("Usage: node build_crossref_authority_report.mjs <input.json> <output.xlsx> [preview-dir]");
const report = JSON.parse(await fs.readFile(inputPath, "utf8"));
const workbook = Workbook.create();
const navy = "#17365D", white = "#FFFFFF", green = "#E2F0D9", blue = "#D9EAF7", amber = "#FFF2CC";
function setup(sheet) { sheet.showGridLines = false; }
function title(sheet, range, text) { sheet.getRange(range).merge(); sheet.getRange(range.split(":")[0]).values = [[text]]; sheet.getRange(range).format = { fill: navy, font: { bold: true, color: white, size: 16 }, verticalAlignment: "center" }; sheet.getRange(range).format.rowHeight = 30; }
function header(range) { range.format = { fill: navy, font: { bold: true, color: white }, horizontalAlignment: "center", verticalAlignment: "center", wrapText: true }; }
function body(range) { range.format = { verticalAlignment: "center", borders: { insideHorizontal: { style: "thin", color: "#D9E2F3" } } }; }

const overview = workbook.worksheets.add("评测总览");
const details = workbook.worksheets.add("DOI明细");
const definitions = workbook.worksheets.add("指标口径");
for (const sheet of [overview, details, definitions]) setup(sheet);

title(overview, "A1:I1", "PaperAgent 普通 DOI Authority Provider：Crossref 首轮评测");
overview.getRange("A3:I3").values = [["快照数", "样本数", "成功查询", "覆盖率", "标题匹配", "标题冲突", "原生查无", "失败", "实际 API"]]; header(overview.getRange("A3:I3"));
overview.getRange("A4:I4").values = [[report.snapshot_count, report.claim_count, report.successful_lookup_count, report.coverage_rate, report.match_count, report.title_conflict_count, report.not_found_count, report.failed_count, report.actual_api_call_count]]; body(overview.getRange("A4:I4")); overview.getRange("D4").format.numberFormat = "0.00%";
overview.getRange("A6:I6").merge(); overview.getRange("A6").values = [["结论：20/20 DOI 查询成功且标题一致，Crossref 具备继续参与 provider 选型评测的资格；样本规模与出版商覆盖仍不足，当前不进入生产默认流程。"]]; overview.getRange("A6:I6").format = { fill: green, font: { bold: true }, wrapText: true };
overview.getRange("A8:I8").merge(); overview.getRange("A8").values = [["边界：网络失败单独计数且不缓存，不得视为 DOI 查无；本轮按三快照稳定 DOI 的字典序抽取，下一轮需按注册机构或出版商分层抽样并加入替代 provider。"]]; overview.getRange("A8:I8").format = { fill: amber, wrapText: true };
overview.getRange("A:I").format.columnWidth = 17;

title(details, "A1:H1", "20 个稳定普通 DOI 的规范标题核验明细");
details.getRange("A3:H3").values = [["DOI", "状态", "标题相似度", "OpenAlex 标题", "Crossref 标题", "出现快照", "案例 ID", "错误码"]]; header(details.getRange("A3:H3"));
const rows = report.rows.map(row => [row.doi, row.status, row.title_similarity, row.claimed_title, row.canonical_title, row.snapshots.join("；"), row.case_ids.join("；"), row.error_code]);
details.getRangeByIndexes(3, 0, rows.length, 8).values = rows; body(details.getRange(`A4:H${3 + rows.length}`)); details.getRange(`C4:C${3 + rows.length}`).format.numberFormat = "0.00%";
details.getRange(`B4:B${3 + rows.length}`).conditionalFormats.add("containsText", { text: "MATCH", format: { fill: green } });
details.freezePanes.freezeRows(3); details.freezePanes.freezeColumns(2); details.getRange("A:H").format.columnWidth = 22; details.getRange("A:A").format.columnWidth = 32; details.getRange("D:E").format.columnWidth = 65;

title(definitions, "A1:D1", "指标计算口径与结果含义");
definitions.getRange("A3:D3").values = [["指标", "计算方式", "通过代表", "失败或异常代表"]]; header(definitions.getRange("A3:D3"));
const defs = [
  ["覆盖率", "成功得到 Crossref 响应的 DOI 数 ÷ 样本 DOI 数", "provider 能覆盖当前样本", "网络、限流或协议问题阻碍验证"],
  ["标题匹配", "OpenAlex 与 Crossref 标题 Jaccard 相似度 ≥ 70%", "两个来源的 DOI 身份声明一致", "低于门槛需人工复核，不能直接自动修复"],
  ["原生查无", "Crossref 请求成功但 paper 为空", "该 provider 明确没有对应记录", "不能与超时、SSL、限流混为一类"],
  ["失败", "工具执行返回 TIMEOUT/RATE_LIMITED/EXECUTION_ERROR 等", "不适用", "不缓存、不隔离，后续允许重试或切换 provider"],
  ["实际 API", "未命中成功缓存时发出的 Crossref 请求数", "可审计本轮网络成本", "异常升高说明缓存或抽样复用失效"],
];
definitions.getRangeByIndexes(3, 0, defs.length, 4).values = defs; body(definitions.getRange("A4:D8")); definitions.getRange("A:A").format.columnWidth = 22; definitions.getRange("B:D").format.columnWidth = 55; definitions.getRange("A3:D8").format.wrapText = true;

console.log((await workbook.inspect({ kind: "table", range: "评测总览!A1:I8", include: "values,formulas", tableMaxRows: 8, tableMaxCols: 9 })).ndjson);
console.log((await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 100 }, summary: "formula errors" })).ndjson);
if (previewDir) { await fs.mkdir(previewDir, { recursive: true }); for (const [sheetName, range] of Object.entries({ "评测总览": "A1:I9", "DOI明细": `A1:H${3 + rows.length}`, "指标口径": "A1:D9" })) { const blob = await workbook.render({ sheetName, range, scale: 1, format: "png" }); await fs.writeFile(path.join(previewDir, `${sheetName}.png`), new Uint8Array(await blob.arrayBuffer())); } }
await fs.mkdir(path.dirname(outputPath), { recursive: true }); const output = await SpreadsheetFile.exportXlsx(workbook); await output.save(outputPath); console.log(`Saved ${outputPath}`);
