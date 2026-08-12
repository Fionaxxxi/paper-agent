import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const [evalPath, baselineList, outputPath, previewDir] = process.argv.slice(2);
if (!evalPath || !baselineList || !outputPath) {
  throw new Error("Usage: node build_canonical_metadata_report.mjs <eval.json> <baseline-a.json;baseline-b.json> <output.xlsx> [preview-dir]");
}

const result = JSON.parse(await fs.readFile(evalPath, "utf8"));
const baselines = await Promise.all(baselineList.split(";").map(async item => JSON.parse(await fs.readFile(item, "utf8"))));
const workbook = Workbook.create();
const colors = { navy: "#17365D", blue: "#D9EAF7", white: "#FFFFFF", green: "#E2F0D9", amber: "#FFF2CC", red: "#FCE4D6", light: "#EEF5FB" };

function setup(sheet) { sheet.showGridLines = false; }
function title(sheet, range, text) {
  sheet.getRange(range).merge();
  sheet.getRange(range.split(":")[0]).values = [[text]];
  sheet.getRange(range).format = { fill: colors.navy, font: { bold: true, color: colors.white, size: 16 }, verticalAlignment: "center" };
  sheet.getRange(range).format.rowHeight = 30;
}
function header(range) { range.format = { fill: colors.navy, font: { bold: true, color: colors.white }, horizontalAlignment: "center", verticalAlignment: "center", wrapText: true }; }
function body(range) { range.format = { verticalAlignment: "center", borders: { insideHorizontal: { style: "thin", color: "#D9E2F3" } } }; }

const overview = workbook.worksheets.add("评测总览");
const metrics = workbook.worksheets.add("指标对比");
const cases = workbook.worksheets.add("逐题对比");
const authority = workbook.worksheets.add("身份验证");
const definitions = workbook.worksheets.add("指标口径");
for (const sheet of [overview, metrics, cases, authority, definitions]) setup(sheet);

title(overview, "A1:H1", "PaperAgent 规范元数据验证候选评测");
overview.getRange("A3:H3").values = [["重点身份", "成功解析", "原生查无", "本次 API", "缓存命中", "LLM Token", "快照数量", "当前结论"]];
header(overview.getRange("A3:H3"));
overview.getRange("A4:H4").values = [[result.claimed_identity_count, result.resolved_identity_count - result.not_found_identity_count, result.not_found_identity_count, result.actual_api_call_count, result.cache_hit_count, 0, result.snapshots.length, result.promotion?.promotion_ready ? "三快照门槛通过" : "暂不晋升"]];
body(overview.getRange("A4:H4"));
overview.getRange("H4").format.wrapText = true;
overview.getRange("A6:H6").merge();
overview.getRange("A6").values = [[`结论：联合 arXiv 与 Crossref authority 在 ${result.snapshots.length} 份快照上相对 v2 的 Recall@5、MRR@5 均提高 5 个百分点；但 Crossref 相对仅 arXiv canonical 的质量与排名增量均为 0，其当前价值是普通 DOI 身份可审计覆盖。`]];
overview.getRange("A6:H6").format = { fill: colors.green, font: { bold: true }, wrapText: true };
overview.getRange("A8:H8").merge();
overview.getRange("A8").values = [["判断边界：arXiv 原生查无可作为无效 arXiv 声明的负证据；Crossref 查无只记录警告、不自动隔离普通 DOI。网络失败不缓存，也不等于查无。"]];
overview.getRange("A8:H8").format = { fill: colors.light, wrapText: true };
overview.getRange("A:H").format.columnWidth = 18;
overview.getRange("H:H").format.columnWidth = 28;
overview.getRange("4:4").format.rowHeight = 30;

title(metrics, "A1:I1", `${result.snapshots.length} 份独立快照：v2 与规范元数据 v3 指标对比`);
metrics.getRange("A3:I3").values = [["快照", "策略", "Recall@5", "Recall 差值", "MRR@5", "MRR 差值", "nDCG@5", "nDCG 差值", "隔离数量"]];
header(metrics.getRange("A3:I3"));
const metricRows = [];
for (let i = 0; i < result.snapshots.length; i++) {
  const candidate = result.snapshots[i];
  const arxivOnly = result.arxiv_only_snapshots[i];
  const baseline = baselines[i].profiles.multi_verified_rerank.summary;
  metricRows.push([candidate.snapshot_id, "v2 词法隔离", baseline.mean_recall_at_5, null, baseline.mean_mrr_at_5, null, baseline.mean_ndcg_at_5, null, baseline.total_metadata_quarantined_count]);
  metricRows.push([candidate.snapshot_id, "仅 arXiv canonical", arxivOnly.summary.mean_recall_at_5, null, arxivOnly.summary.mean_mrr_at_5, null, arxivOnly.summary.mean_ndcg_at_5, null, arxivOnly.summary.total_metadata_quarantined_count]);
  metricRows.push([candidate.snapshot_id, "arXiv + Crossref", candidate.summary.mean_recall_at_5, null, candidate.summary.mean_mrr_at_5, null, candidate.summary.mean_ndcg_at_5, null, candidate.summary.total_metadata_quarantined_count]);
}
metrics.getRangeByIndexes(3, 0, metricRows.length, 9).values = metricRows;
for (let row = 4; row <= 3 + metricRows.length; row += 3) {
  for (const current of [row + 1, row + 2]) {
    metrics.getRange(`D${current}`).formulas = [[`=C${current}-C${row}`]];
    metrics.getRange(`F${current}`).formulas = [[`=E${current}-E${row}`]];
    metrics.getRange(`H${current}`).formulas = [[`=G${current}-G${row}`]];
  }
}
body(metrics.getRange(`A4:I${3 + metricRows.length}`));
metrics.getRange(`C4:H${3 + metricRows.length}`).format.numberFormat = "0.00%";
metrics.getRange("A:I").format.columnWidth = 18;
metrics.getRange("A:A").format.columnWidth = 24;

title(cases, "A1:J1", "逐题质量变化（规范候选相对 v2）");
cases.getRange("A3:J3").values = [["快照", "案例 ID", "查询", "v2 Recall@5", "v3 Recall@5", "Recall 差值", "v2 MRR@5", "v3 MRR@5", "MRR 差值", "隔离数量"]];
header(cases.getRange("A3:J3"));
const caseRows = [];
for (let i = 0; i < result.snapshots.length; i++) {
  const candidate = result.snapshots[i];
  const baselineCases = new Map(baselines[i].profiles.multi_verified_rerank.cases.map(item => [item.case_id, item]));
  for (const item of candidate.cases) {
    const base = baselineCases.get(item.case_id);
    caseRows.push([candidate.snapshot_id, item.case_id, item.query, base.recall_at_5, item.recall_at_5, item.recall_at_5 - base.recall_at_5, base.mrr_at_5, item.mrr_at_5, item.mrr_at_5 - base.mrr_at_5, item.metadata_quarantined_count]);
  }
}
cases.getRangeByIndexes(3, 0, caseRows.length, 10).values = caseRows;
body(cases.getRange(`A4:J${3 + caseRows.length}`));
cases.getRange(`D4:I${3 + caseRows.length}`).format.numberFormat = "0.00%";
cases.freezePanes.freezeRows(3); cases.freezePanes.freezeColumns(2);
cases.getRange("A:J").format.columnWidth = 16; cases.getRange("A:B").format.columnWidth = 24; cases.getRange("C:C").format.columnWidth = 62;
cases.getRange(`C4:C${3 + caseRows.length}`).format.wrapText = true;
cases.getRange(`4:${3 + caseRows.length}`).format.rowHeight = 28;

title(authority, "A1:C1", "规范身份查询结果");
authority.getRange("A3:C3").values = [["规范身份", "查询状态", "原生标题"]];
header(authority.getRange("A3:C3"));
const authorityRows = result.authority_records.map(item => [item.canonical_identity, item.status, item.canonical_title]);
authority.getRangeByIndexes(3, 0, authorityRows.length, 3).values = authorityRows;
body(authority.getRange(`A4:C${3 + authorityRows.length}`));
authority.getRange(`B4:B${3 + authorityRows.length}`).conditionalFormats.add("containsText", { text: "RESOLVED", format: { fill: colors.green } });
authority.getRange(`B4:B${3 + authorityRows.length}`).conditionalFormats.add("containsText", { text: "NOT_FOUND", format: { fill: colors.red } });
authority.getRange("A:A").format.columnWidth = 28; authority.getRange("B:B").format.columnWidth = 18; authority.getRange("C:C").format.columnWidth = 75;

title(definitions, "A1:D1", "指标计算口径与结果含义");
definitions.getRange("A3:D3").values = [["指标", "计算方式", "本轮用途", "结果如何解释"]];
header(definitions.getRange("A3:D3"));
const definitionRows = [
  ["Recall@5", "前 5 条中命中的相关论文数 ÷ 标注相关论文总数，再对案例取平均", "检查规范修复是否找回被误隔离论文", "提高表示召回改善；下降表示发生误伤"],
  ["MRR@5", "首篇相关论文名次的倒数；前 5 条无命中为 0，再对案例取平均", "检查相关论文是否更早出现", "提高表示用户更快看到首篇正确论文"],
  ["nDCG@5", "前 5 条按分级相关性计算 DCG，再除以理想排序 IDCG", "检查整体排序位置与相关性等级", "提高表示排序更接近理想顺序"],
  ["隔离数量", "被元数据策略排除出候选排序的唯一记录数", "观察规则是否过度删除", "减少不一定更好，必须同时看质量和规范证据"],
  ["成功解析", "重点 arXiv 身份中取得原生论文记录的数量", "衡量规范证据覆盖", "只有取得原生记录才允许修复身份字段"],
  ["权威查无", "provider 查询成功但没有对应记录的数量", "审计规范源覆盖", "arXiv 查无可隔离相应声明；Crossref 查无只警告，不自动隔离"],
];
definitions.getRangeByIndexes(3, 0, definitionRows.length, 4).values = definitionRows;
body(definitions.getRange(`A4:D${3 + definitionRows.length}`));
definitions.getRange("A:A").format.columnWidth = 22; definitions.getRange("B:D").format.columnWidth = 55; definitions.getRange("A3:D10").format.wrapText = true;

const check = await workbook.inspect({ kind: "table", range: `指标对比!A1:I${3 + metricRows.length}`, include: "values,formulas", tableMaxRows: 12, tableMaxCols: 9 });
console.log(check.ndjson);
const errors = await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 100 }, summary: "formula errors" });
console.log(errors.ndjson);
if (previewDir) {
  await fs.mkdir(previewDir, { recursive: true });
  const ranges = { "评测总览": "A1:H9", "指标对比": `A1:I${3 + metricRows.length}`, "逐题对比": `A1:J${3 + caseRows.length}`, "身份验证": `A1:C${3 + authorityRows.length}`, "指标口径": "A1:D10" };
  for (const [sheetName, range] of Object.entries(ranges)) {
    const preview = await workbook.render({ sheetName, range, scale: 1, format: "png" });
    await fs.writeFile(path.join(previewDir, `${sheetName}.png`), new Uint8Array(await preview.arrayBuffer()));
  }
}
await fs.mkdir(path.dirname(outputPath), { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(`Saved ${outputPath}`);
