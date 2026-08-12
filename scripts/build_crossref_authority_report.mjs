import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const [inputPath, outputPath, previewDir] = process.argv.slice(2);
if (!inputPath || !outputPath) throw new Error("Usage: node build_crossref_authority_report.mjs <input.json> <output.xlsx> [preview-dir]");
const report = JSON.parse(await fs.readFile(inputPath, "utf8"));
const workbook = Workbook.create();
const navy = "#17365D", white = "#FFFFFF", green = "#E2F0D9", blue = "#D9EAF7", amber = "#FFF2CC", red = "#FCE4D6";
function setup(sheet) { sheet.showGridLines = false; }
function title(sheet, range, text) { const r = sheet.getRange(range); r.merge(); r.getCell(0, 0).values = [[text]]; r.format = { fill: navy, font: { bold: true, color: white, size: 16 }, verticalAlignment: "center" }; r.format.rowHeight = 30; }
function header(range) { range.format = { fill: navy, font: { bold: true, color: white }, horizontalAlignment: "center", verticalAlignment: "center", wrapText: true }; }
function body(range) { range.format = { verticalAlignment: "center", borders: { insideHorizontal: { style: "thin", color: "#D9E2F3" } } }; }

const overview = workbook.worksheets.add("评测总览");
const strata = workbook.worksheets.add("分层覆盖");
const details = workbook.worksheets.add("Provider明细");
const definitions = workbook.worksheets.add("指标口径");
for (const sheet of [overview, strata, details, definitions]) setup(sheet);

title(overview, "A1:J1", "PaperAgent 普通 DOI Authority Provider 分层对比评测");
overview.getRange("A2:J2").merge(); overview.getRange("A2").values = [[`稳定候选 ${report.population_size} 条；按 DOI 前缀轮转抽样 ${report.sample_size} 条；覆盖 ${report.represented_prefix_count} 个前缀；三份独立快照。`]];
overview.getRange("A4:J4").values = [["Provider", "样本", "明确响应", "覆盖率", "标题匹配", "标题冲突", "查无", "失败", "实际 API", "缓存命中"]]; header(overview.getRange("A4:J4"));
const summaryRows = report.provider_results.map(r => [r.provider, r.claim_count, r.successful_lookup_count, r.coverage_rate, r.match_count, r.title_conflict_count, r.not_found_count, r.failed_count, r.actual_api_call_count, r.cache_hit_count]);
overview.getRangeByIndexes(4, 0, summaryRows.length, 10).values = summaryRows; body(overview.getRange(`A5:J${4 + summaryRows.length}`)); overview.getRange(`D5:D${4 + summaryRows.length}`).format.numberFormat = "0.00%";
overview.getRange("A8:J8").merge(); overview.getRange("A8").values = [[`双方均返回标题的 ${report.provider_comparison.comparable_count} 条中，${report.provider_comparison.title_agreement_count} 条一致（${(report.provider_comparison.title_agreement_rate * 100).toFixed(2)}%）。`]]; overview.getRange("A8:J8").format = { fill: blue, font: { bold: true } };
overview.getRange("A10:J10").merge(); overview.getRange("A10").values = [["结论：Crossref 在当前网络条件下响应完整且稳定，可进入下一轮生产 A/B；Semantic Scholar 数据一致性较高，但匿名访问发生限流，保留为配置 API Key 后复测的候选，不能据此判定其语料覆盖较差。"]]; overview.getRange("A10:J10").format = { fill: green, font: { bold: true }, wrapText: true }; overview.getRange("A10:J10").format.rowHeight = 45;
overview.getRange("A12:J12").merge(); overview.getRange("A12").values = [["安全边界：本轮只评估 provider，不改变生产默认；FAILED 不等于 NOT_FOUND，不进入论文隔离证据。"]]; overview.getRange("A12:J12").format = { fill: amber, wrapText: true };
overview.getRange("A:J").format.columnWidth = 17;

const prefixes = [...new Set(report.rows.map(r => r.doi_prefix))].sort();
title(strata, "A1:F1", "DOI 前缀分层覆盖");
strata.getRange("A3:F3").values = [["DOI 前缀", "样本数", "Crossref 匹配", "Crossref 查无/失败", "Semantic Scholar 匹配", "Semantic Scholar 查无/失败"]]; header(strata.getRange("A3:F3"));
const strataRows = prefixes.map(prefix => { const rows = report.rows.filter(r => r.doi_prefix === prefix); const c = rows.filter(r => r.provider === "crossref"), s = rows.filter(r => r.provider === "semantic_scholar"); return [prefix, c.length, c.filter(r => r.status === "MATCH").length, c.filter(r => r.status !== "MATCH").length, s.filter(r => r.status === "MATCH").length, s.filter(r => r.status !== "MATCH").length]; });
strata.getRangeByIndexes(3, 0, strataRows.length, 6).values = strataRows; body(strata.getRange(`A4:F${3 + strataRows.length}`)); strata.freezePanes.freezeRows(3); strata.getRange("A:F").format.columnWidth = 25;

title(details, "A1:L1", "分层样本逐 Provider 审计明细");
details.getRange("A3:L3").values = [["DOI", "前缀", "Provider", "状态", "标题相似度", "OpenAlex 标题", "Provider 标题", "声明年份", "规范年份", "案例 ID", "错误码", "错误信息"]]; header(details.getRange("A3:L3"));
const rows = report.rows.map(r => [r.doi, r.doi_prefix, r.provider, r.status, r.title_similarity, r.claimed_title, r.canonical_title, r.claimed_year ?? "", r.canonical_year ?? "", r.case_ids.join("；"), r.error_code, r.error_message ?? ""]);
details.getRangeByIndexes(3, 0, rows.length, 12).values = rows; body(details.getRange(`A4:L${3 + rows.length}`)); details.getRange(`E4:E${3 + rows.length}`).format.numberFormat = "0.00%";
details.getRange(`D4:D${3 + rows.length}`).conditionalFormats.add("containsText", { text: "MATCH", format: { fill: green } }); details.getRange(`D4:D${3 + rows.length}`).conditionalFormats.add("containsText", { text: "FAILED", format: { fill: red } });
details.freezePanes.freezeRows(3); details.freezePanes.freezeColumns(3); details.getRange("A:L").format.columnWidth = 20; details.getRange("A:A").format.columnWidth = 32; details.getRange("F:G").format.columnWidth = 55; details.getRange("L:L").format.columnWidth = 55;

title(definitions, "A1:D1", "指标计算口径与选型边界");
definitions.getRange("A3:D3").values = [["指标", "计算方式", "通过代表", "限制/失败含义"]]; header(definitions.getRange("A3:D3"));
const defs = [
  ["分层抽样", "按 DOI 前缀分组后轮转取样，直到达到样本数", "避免 10.18653 等高频前缀垄断样本", "仅代表当前稳定 DOI 总体，不等于全学科随机抽样"],
  ["覆盖率", "非 FAILED 的明确响应数 ÷ 样本数", "provider 可明确返回论文或查无结论", "网络失败单列，不伪装成数据查无"],
  ["标题匹配", "OpenAlex 与 provider 标题词集 Jaccard ≥ 70%", "同一 DOI 的身份声明基本一致", "低于阈值进入人工复核，不能自动修复"],
  ["Provider 一致率", "两个 provider 均返回标题且相互相似度 ≥ 70% 的数量 ÷ 可比数量", "两个外部来源对身份元数据相互印证", "只在双方成功返回时计算"],
  ["查无", "HTTP 请求成功但 paper 为空", "provider 明确无对应记录", "可作为 provider 覆盖信号，但尚不能直接隔离论文"],
  ["失败", "TIMEOUT、RATE_LIMITED、EXECUTION_ERROR 等", "不适用", "不缓存、不作为负证据，允许重试或换 provider"],
];
definitions.getRangeByIndexes(3, 0, defs.length, 4).values = defs; body(definitions.getRange("A4:D9")); definitions.getRange("A:A").format.columnWidth = 24; definitions.getRange("B:D").format.columnWidth = 55; definitions.getRange("A3:D9").format.wrapText = true;

console.log((await workbook.inspect({ kind: "table", range: "评测总览!A1:J12", include: "values,formulas", tableMaxRows: 12, tableMaxCols: 10 })).ndjson);
console.log((await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 100 }, summary: "formula errors" })).ndjson);
if (previewDir) { await fs.mkdir(previewDir, { recursive: true }); for (const [sheetName, range] of Object.entries({ "评测总览": "A1:J12", "分层覆盖": `A1:F${3 + strataRows.length}`, "Provider明细": `A1:L${3 + rows.length}`, "指标口径": "A1:D9" })) { const blob = await workbook.render({ sheetName, range, scale: 1, format: "png" }); await fs.writeFile(path.join(previewDir, `${sheetName}.png`), new Uint8Array(await blob.arrayBuffer())); } }
await fs.mkdir(path.dirname(outputPath), { recursive: true }); const output = await SpreadsheetFile.exportXlsx(workbook); await output.save(outputPath); console.log(`Saved ${outputPath}`);
