import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const [comparisonPath, manifestPath, outputPath, previewDir] = process.argv.slice(2);
if (!comparisonPath || !manifestPath || !outputPath) {
  throw new Error("Usage: node build_snapshot_comparison_report.mjs <comparison.json> <manifest.json> <output.xlsx> [preview-dir]");
}

const comparison = JSON.parse(await fs.readFile(comparisonPath, "utf8"));
const manifest = JSON.parse(await fs.readFile(manifestPath, "utf8"));
const workbook = Workbook.create();
const colors = {
  navy: "#17365D", blue: "#D9EAF7", light: "#EEF5FB", white: "#FFFFFF",
  green: "#E2F0D9", red: "#FCE4D6", amber: "#FFF2CC", gray: "#E7E6E6",
};

function setup(sheet) { sheet.showGridLines = false; }
function title(sheet, range, text) {
  sheet.getRange(range).merge();
  sheet.getRange(range.split(":")[0]).values = [[text]];
  sheet.getRange(range).format = { fill: colors.navy, font: { bold: true, color: colors.white, size: 16 }, verticalAlignment: "center" };
  sheet.getRange(range).format.rowHeight = 30;
}
function header(range) {
  range.format = { fill: colors.navy, font: { bold: true, color: colors.white }, horizontalAlignment: "center", verticalAlignment: "center", wrapText: true };
}
function body(range) {
  range.format = { verticalAlignment: "center", borders: { insideHorizontal: { style: "thin", color: "#D9E2F3" } } };
}
function addTable(sheet, range, name) { sheet.tables.add(range, true, name).style = "TableStyleMedium2"; }

const overview = workbook.worksheets.add("比较总览");
const profiles = workbook.worksheets.add("配置差异");
const cases = workbook.worksheets.add("逐题差异");
const quarantine = workbook.worksheets.add("隔离变更");
const runs = workbook.worksheets.add("运行成本");
for (const sheet of [overview, profiles, cases, quarantine, runs]) setup(sheet);

title(overview, "A1:H1", "PaperAgent 独立检索快照对比");
overview.getRange("A2:H2").merge();
overview.getRange("A2").values = [[`基线：${comparison.baseline_snapshot_id} | 候选：${comparison.candidate_snapshot_id} | 数据集：${comparison.dataset_version} | 目标：${comparison.target_profile}`]];
overview.getRange("A2:H2").format = { fill: colors.light, wrapText: true };
overview.getRange("A4:H4").merge();
overview.getRange("A4").values = [[comparison.promotion_ready ? "结论：满足当前晋升门槛" : `结论：暂不晋升；阻塞原因：${comparison.promotion_blockers.join("、")}`]];
overview.getRange("A4:H4").format = { fill: comparison.promotion_ready ? colors.green : colors.amber, font: { bold: true }, wrapText: true };
overview.getRange("A6:H6").values = [["基线完整", "候选完整", "逐题回归", "基线隔离", "候选隔离", "稳定隔离", "隔离稳定度", "要求稳定度"]];
header(overview.getRange("A6:H6"));
overview.getRange("A7:H7").values = [[comparison.baseline_complete ? "是" : "否", comparison.candidate_complete ? "是" : "否", comparison.critical_regression_count, comparison.quarantine.baseline_count, comparison.quarantine.candidate_count, comparison.quarantine.stable_count, comparison.quarantine.jaccard_stability, comparison.quarantine.required_stability]];
body(overview.getRange("A7:H7"));
overview.getRange("G7:H7").format.numberFormat = "0.00%";
overview.getRange("A10:H10").merge();
overview.getRange("A10").values = [["解读：平均质量没有下降，但隔离集合跨快照漂移时，不能仅凭 Recall/MRR 不变就默认启用。新增与移除记录需要人工或规范元数据源复核。"]];
overview.getRange("A10:H10").format = { fill: colors.light, wrapText: true };
overview.getRange("A:H").format.columnWidth = 18;

const profileRows = comparison.profile_deltas ?? [];
title(profiles, "A1:J1", "各检索配置跨快照指标差异");
profiles.getRange("A3:J3").values = [["配置", "基线 Recall@5", "候选 Recall@5", "Recall 差值", "基线 MRR@5", "候选 MRR@5", "MRR 差值", "基线 nDCG@5", "候选 nDCG@5", "nDCG 差值"]];
header(profiles.getRange("A3:J3"));
if (profileRows.length) {
  profiles.getRangeByIndexes(3, 0, profileRows.length, 10).values = profileRows.map(r => [r.profile, r.baseline_recall_at_5, r.candidate_recall_at_5, r.delta_recall_at_5, r.baseline_mrr_at_5, r.candidate_mrr_at_5, r.delta_mrr_at_5, r.baseline_ndcg_at_5, r.candidate_ndcg_at_5, r.delta_ndcg_at_5]);
  const end = profileRows.length + 3; body(profiles.getRange(`A4:J${end}`)); profiles.getRange(`B4:J${end}`).format.numberFormat = "0.00%"; addTable(profiles, `A3:J${end}`, "SnapshotProfileDeltas");
}
profiles.freezePanes.freezeRows(3); profiles.getRange("A:J").format.columnWidth = 18; profiles.getRange("A:A").format.columnWidth = 26;

const caseRows = comparison.case_deltas ?? [];
title(cases, "A1:K1", "目标策略逐题质量差异");
cases.getRange("A3:K3").values = [["案例ID", "查询", "基线 Recall@5", "候选 Recall@5", "Recall 差值", "基线 MRR@5", "候选 MRR@5", "MRR 差值", "基线 nDCG@5", "候选 nDCG@5", "回归指标"]];
header(cases.getRange("A3:K3"));
if (caseRows.length) {
  cases.getRangeByIndexes(3, 0, caseRows.length, 11).values = caseRows.map(r => [r.case_id, r.query, r.baseline_recall_at_5, r.candidate_recall_at_5, r.delta_recall_at_5, r.baseline_mrr_at_5, r.candidate_mrr_at_5, r.delta_mrr_at_5, r.baseline_ndcg_at_5, r.candidate_ndcg_at_5, (r.regressed_metrics ?? []).join("；")]);
  const end = caseRows.length + 3; body(cases.getRange(`A4:K${end}`)); cases.getRange(`C4:J${end}`).format.numberFormat = "0.00%"; addTable(cases, `A3:K${end}`, "SnapshotCaseDeltas");
}
cases.freezePanes.freezeRows(3); cases.freezePanes.freezeColumns(1); cases.getRange("A:K").format.columnWidth = 16; cases.getRange("A:A").format.columnWidth = 25; cases.getRange("B:B").format.columnWidth = 60;

const quarantineRows = comparison.quarantine?.changes ?? [];
title(quarantine, "A1:G1", "隔离候选稳定性与人工复核清单");
quarantine.getRange("A3:G3").values = [["变化", "案例ID", "查询", "规范身份", "标题", "来源", "警告"]];
header(quarantine.getRange("A3:G3"));
if (quarantineRows.length) {
  quarantine.getRangeByIndexes(3, 0, quarantineRows.length, 7).values = quarantineRows.map(r => [r.change, r.case_id, r.query, r.canonical_identity, r.title, r.source, (r.warnings ?? []).join("；")]);
  const end = quarantineRows.length + 3; body(quarantine.getRange(`A4:G${end}`)); addTable(quarantine, `A3:G${end}`, "QuarantineChanges");
  quarantine.getRange(`A4:A${end}`).conditionalFormats.add("containsText", { text: "added", format: { fill: colors.amber } });
  quarantine.getRange(`A4:A${end}`).conditionalFormats.add("containsText", { text: "removed", format: { fill: colors.red } });
  quarantine.getRange(`A4:A${end}`).conditionalFormats.add("containsText", { text: "stable", format: { fill: colors.green } });
}
quarantine.freezePanes.freezeRows(3); quarantine.freezePanes.freezeColumns(2); quarantine.getRange("A:G").format.columnWidth = 20; quarantine.getRange("C:C").format.columnWidth = 55; quarantine.getRange("E:E").format.columnWidth = 65; quarantine.getRange("G:G").format.columnWidth = 38;

const runRows = manifest.runs ?? [];
title(runs, "A1:F1", "候选快照采集运行与累计成本");
runs.getRange("A3:F3").values = [["运行序号", "运行时间", "Git Commit", "实际 API 调用", "缓存命中", "OpenAlex Key"]];
header(runs.getRange("A3:F3"));
if (runRows.length) {
  runs.getRangeByIndexes(3, 0, runRows.length, 6).values = runRows.map((r, i) => [i + 1, r.generated_at, r.git_commit, r.acquisition.actual_api_call_count ?? 0, r.acquisition.provider_cache_hit_count ?? 0, r.acquisition.openalex_api_key_configured ? "已配置" : "未配置"]);
  const end = runRows.length + 3; body(runs.getRange(`A4:F${end}`)); addTable(runs, `A3:F${end}`, "SnapshotRuns");
}
runs.getRange("A8:C8").values = [["累计运行次数", "累计 API 调用", "累计缓存命中"]]; header(runs.getRange("A8:C8"));
runs.getRange("A9:C9").values = [[manifest.cumulative_acquisition?.run_count ?? 0, manifest.cumulative_acquisition?.actual_api_call_count ?? 0, manifest.cumulative_acquisition?.provider_cache_hit_count ?? 0]]; body(runs.getRange("A9:C9"));
runs.getRange("A:F").format.columnWidth = 22; runs.getRange("C:C").format.columnWidth = 44;

const check = await workbook.inspect({ kind: "table", range: "比较总览!A1:H11", include: "values,formulas", tableMaxRows: 11, tableMaxCols: 8 });
console.log(check.ndjson);
const errors = await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 100 }, summary: "formula errors" });
console.log(errors.ndjson);
if (previewDir) {
  await fs.mkdir(previewDir, { recursive: true });
  const ranges = { 比较总览: "A1:H11", 配置差异: `A1:J${Math.max(profileRows.length + 3, 8)}`, 逐题差异: `A1:K${Math.max(caseRows.length + 3, 8)}`, 隔离变更: `A1:G${Math.max(quarantineRows.length + 3, 8)}`, 运行成本: "A1:F10" };
  for (const [sheetName, range] of Object.entries(ranges)) {
    const preview = await workbook.render({ sheetName, range, scale: 1, format: "png" });
    await fs.writeFile(path.join(previewDir, `${sheetName}.png`), new Uint8Array(await preview.arrayBuffer()));
  }
}
await fs.mkdir(path.dirname(outputPath), { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(`Saved ${outputPath}`);
