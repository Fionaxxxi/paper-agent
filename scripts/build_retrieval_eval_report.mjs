import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const [reportPath, datasetPath, outputPath, previewDir] = process.argv.slice(2);
if (!reportPath || !datasetPath || !outputPath) {
  throw new Error("Usage: node build_retrieval_eval_report.mjs <report.json> <dataset.json> <output.xlsx> [preview-dir]");
}

const report = JSON.parse(await fs.readFile(reportPath, "utf8"));
const dataset = JSON.parse(await fs.readFile(datasetPath, "utf8"));
const workbook = Workbook.create();
const COLORS = {
  navy: "#17365D", blue: "#D9EAF7", light: "#EEF5FB", white: "#FFFFFF",
  green: "#E2F0D9", red: "#FCE4D6", amber: "#FFF2CC", gray: "#E7E6E6",
  border: "#B4C6E7", text: "#404040",
};

function title(sheet, range, value) {
  sheet.getRange(range).merge();
  sheet.getRange(range.split(":")[0]).values = [[value]];
  sheet.getRange(range).format = { fill: COLORS.navy, font: { bold: true, color: COLORS.white, size: 16 }, verticalAlignment: "center" };
  sheet.getRange(range).format.rowHeight = 30;
}
function header(range) {
  range.format = { fill: COLORS.navy, font: { bold: true, color: COLORS.white }, horizontalAlignment: "center", verticalAlignment: "center", wrapText: true };
}
function body(range) {
  range.format = { verticalAlignment: "center", borders: { insideHorizontal: { style: "thin", color: "#D9E2F3" } } };
}
function setup(sheet) { sheet.showGridLines = false; }
function table(sheet, range, name) { sheet.tables.add(range, true, name).style = "TableStyleMedium2"; }
function statusFormatting(range) {
  range.conditionalFormats.add("containsText", { text: "success", format: { fill: COLORS.green } });
  range.conditionalFormats.add("containsText", { text: "empty", format: { fill: COLORS.amber } });
  range.conditionalFormats.add("containsText", { text: "failed", format: { fill: COLORS.red } });
  range.conditionalFormats.add("containsText", { text: "skipped", format: { fill: COLORS.gray } });
  range.conditionalFormats.add("containsText", { text: "partial", format: { fill: COLORS.amber } });
}

const overview = workbook.worksheets.add("评测总览");
const casesSheet = workbook.worksheets.add("逐题指标");
const papersSheet = workbook.worksheets.add("论文排名");
const goldSheet = workbook.worksheets.add("金标准");
const exceptionsSheet = workbook.worksheets.add("异常与跳过");
const metricsSheet = workbook.worksheets.add("指标说明");
for (const sheet of [overview, casesSheet, papersSheet, goldSheet, exceptionsSheet, metricsSheet]) setup(sheet);

const profiles = Object.entries(report.profiles ?? {});
title(overview, "A1:P1", "PaperAgent 在线论文检索评测");
overview.getRange("A2:P2").merge();
overview.getRange("A2").values = [[`数据集：${report.dataset_name} v${report.dataset_version}（${report.dataset_case_count} 题） | 运行：${report.generated_at} | Git：${report.git_commit}`]];
overview.getRange("A2:P2").format = { fill: COLORS.light, font: { color: COLORS.text }, wrapText: true };
const complete = report.acquisition?.openalex_api_key_configured && profiles.every(([, p]) => Number(p.summary.failed_count ?? 0) === 0);
overview.getRange("A4:P4").merge();
overview.getRange("A4").values = [[complete ? "结论状态：数据完整，可进入来源比较复核。" : "结论状态：阶段结果。OpenAlex 未配置 API Key 或仍有失败，不能据此决定多来源优劣。"]];
overview.getRange("A4:P4").format = { fill: complete ? COLORS.green : COLORS.amber, font: { bold: true, color: COLORS.text }, wrapText: true };
overview.getRange("A6:P6").values = [["配置", "题数", "成功", "部分成功", "空结果", "失败", "跳过", "Recall@5", "MRR@5", "nDCG@5", "空结果率", "失败率", "P50 延迟(秒)", "P95 延迟(秒)", "来源调用", "缓存命中"]];
header(overview.getRange("A6:P6"));
if (profiles.length) {
  overview.getRangeByIndexes(6, 0, profiles.length, 16).values = profiles.map(([name, payload]) => {
    const s = payload.summary;
    return [name, s.case_count, s.success_count, s.partial_success_count, s.empty_count ?? 0, s.failed_count, s.skipped_count, s.mean_recall_at_5, s.mean_mrr_at_5, s.mean_ndcg_at_5, s.empty_result_rate_pct / 100, s.failure_rate_pct / 100, s.p50_network_latency_seconds, s.p95_network_latency_seconds, s.total_provider_calls, s.total_cache_hits];
  });
  const end = 6 + profiles.length;
  body(overview.getRange(`A7:P${end}`));
  overview.getRange(`H7:L${end}`).format.numberFormat = "0.00%";
  overview.getRange(`M7:N${end}`).format.numberFormat = "0.000";
  table(overview, `A6:P${end}`, "RetrievalSummaryTable");
}
overview.getRange("A11:D11").values = [["实际 API 调用", "缓存命中", "OpenAlex Key", "报告模式"]];
header(overview.getRange("A11:D11"));
overview.getRange("A12:D12").values = [[report.acquisition?.actual_api_call_count ?? 0, report.acquisition?.provider_cache_hit_count ?? 0, report.acquisition?.openalex_api_key_configured ? "已配置" : "未配置", report.mode ?? ""]];
body(overview.getRange("A12:D12"));
overview.freezePanes.freezeRows(6);
overview.getRange("A:P").format.columnWidth = 14;
overview.getRange("A:A").format.columnWidth = 16;

const caseRows = profiles.flatMap(([, payload]) => payload.cases ?? []);
const caseHeaders = ["配置", "案例ID", "查询", "语言", "类别", "难度", "状态", "Recall@1", "Recall@3", "Recall@5", "Precision@5", "MRR@5", "nDCG@5", "维度覆盖率", "返回数", "重复率", "网络延迟(秒)", "缓存命中", "来源错误"];
title(casesSheet, "A1:S1", "逐题检索指标");
casesSheet.getRange("A3:S3").values = [caseHeaders]; header(casesSheet.getRange("A3:S3"));
if (caseRows.length) {
  casesSheet.getRangeByIndexes(3, 0, caseRows.length, caseHeaders.length).values = caseRows.map(c => [c.profile, c.case_id, c.query, c.language, c.category, c.difficulty, c.status, c.recall_at_1, c.recall_at_3, c.recall_at_5, c.precision_at_5, c.mrr_at_5, c.ndcg_at_5, c.dimension_coverage_pct / 100, c.returned_count, c.duplicate_rate_pct / 100, c.network_latency_seconds, c.cache_hit_count, (c.provider_errors ?? []).map(e => `${e.provider}:${e.error_code}`).join("；")]);
  const end = caseRows.length + 3; body(casesSheet.getRange(`A4:S${end}`));
  casesSheet.getRange(`H4:N${end}`).format.numberFormat = "0.00%"; casesSheet.getRange(`P4:P${end}`).format.numberFormat = "0.00%"; casesSheet.getRange(`Q4:Q${end}`).format.numberFormat = "0.000";
  statusFormatting(casesSheet.getRange(`G4:G${end}`)); table(casesSheet, `A3:S${end}`, "RetrievalCasesTable");
}
casesSheet.freezePanes.freezeRows(3); casesSheet.freezePanes.freezeColumns(2);
casesSheet.getRange("A:S").format.columnWidth = 13; casesSheet.getRange("B:B").format.columnWidth = 24; casesSheet.getRange("C:C").format.columnWidth = 55; casesSheet.getRange("S:S").format.columnWidth = 28;

const paperRows = caseRows.flatMap(c => (c.ranked_papers ?? []).map(p => [c.profile, c.case_id, c.query, p.rank, p.title, p.source, p.entry_id, p.doi, p.is_relevant ? "是" : "否", p.relevance_grade, p.matched_gold_title, p.pdf_url]));
title(papersSheet, "A1:L1", "返回论文排名与金标准匹配");
papersSheet.getRange("A3:L3").values = [["配置", "案例ID", "查询", "排名", "论文标题", "来源", "Entry ID", "DOI", "命中金标准", "相关性等级", "匹配金标准标题", "PDF URL"]]; header(papersSheet.getRange("A3:L3"));
if (paperRows.length) { papersSheet.getRangeByIndexes(3, 0, paperRows.length, 12).values = paperRows; const end = paperRows.length + 3; body(papersSheet.getRange(`A4:L${end}`)); table(papersSheet, `A3:L${end}`, "RankedPapersTable"); }
papersSheet.freezePanes.freezeRows(3); papersSheet.freezePanes.freezeColumns(2); papersSheet.getRange("A:L").format.columnWidth = 15; papersSheet.getRange("C:C").format.columnWidth = 45; papersSheet.getRange("E:E").format.columnWidth = 55; papersSheet.getRange("K:L").format.columnWidth = 45;

const goldRows = (dataset.cases ?? []).flatMap(c => (c.relevant_papers ?? []).map(p => [c.id, c.query, c.language, c.category, c.difficulty, (c.required_dimensions ?? []).join("；"), p.title, p.arxiv_id ?? "", p.doi ?? "", p.relevance_grade]));
title(goldSheet, "A1:J1", `检索金标准（${dataset.dataset_name} v${dataset.dataset_version}）`);
goldSheet.getRange("A3:J3").values = [["案例ID", "查询", "语言", "类别", "难度", "必要覆盖维度", "相关论文标题", "arXiv ID", "DOI", "相关性等级"]]; header(goldSheet.getRange("A3:J3"));
if (goldRows.length) { goldSheet.getRangeByIndexes(3, 0, goldRows.length, 10).values = goldRows; const end = goldRows.length + 3; body(goldSheet.getRange(`A4:J${end}`)); table(goldSheet, `A3:J${end}`, "GoldStandardTable"); }
goldSheet.freezePanes.freezeRows(3); goldSheet.freezePanes.freezeColumns(1); goldSheet.getRange("A:J").format.columnWidth = 18; goldSheet.getRange("B:B").format.columnWidth = 55; goldSheet.getRange("F:G").format.columnWidth = 50;

const exceptionRows = caseRows.flatMap(c => (c.provider_errors ?? []).map(e => [c.profile, c.case_id, c.query, c.status, e.provider, e.error_code, e.error_message]));
title(exceptionsSheet, "A1:G1", "来源失败、缺少凭据与跳过明细");
exceptionsSheet.getRange("A3:G3").values = [["配置", "案例ID", "查询", "案例状态", "来源", "错误码", "错误说明"]]; header(exceptionsSheet.getRange("A3:G3"));
if (exceptionRows.length) { exceptionsSheet.getRangeByIndexes(3, 0, exceptionRows.length, 7).values = exceptionRows; const end = exceptionRows.length + 3; body(exceptionsSheet.getRange(`A4:G${end}`)); statusFormatting(exceptionsSheet.getRange(`D4:D${end}`)); table(exceptionsSheet, `A3:G${end}`, "RetrievalExceptionsTable"); }
exceptionsSheet.freezePanes.freezeRows(3); exceptionsSheet.getRange("A:G").format.columnWidth = 20; exceptionsSheet.getRange("C:C").format.columnWidth = 55; exceptionsSheet.getRange("G:G").format.columnWidth = 70;

const metricRows = [
  ["Recall@K", "前 K 条命中的不同金标准论文数 / 金标准论文总数", "越高越好；反映遗漏程度"],
  ["Precision@K", "前 K 条命中的不同金标准论文数 / K", "越高越好；不足 K 条仍以 K 为分母"],
  ["MRR@K", "1 / 第一篇相关论文排名；无命中为 0", "越高越好；强调首个有效结果位置"],
  ["nDCG@K", "DCG@K / 理想 DCG@K", "越高越好；兼顾相关性等级与排序"],
  ["维度覆盖率", "已命中的必要维度数 / 必要维度总数", "越高越好；检查研究角度覆盖"],
  ["重复率", "(合并前数量 - 合并后数量) / 合并前数量", "通常越低越好，但需与 Recall 联合分析"],
  ["失败率", "执行失败案例数 / 完整案例数", "越低越好；不包含正常空结果"],
  ["空结果率", "返回零篇论文案例数 / 完整案例数", "越低越好；与网络失败分开"],
];
title(metricsSheet, "A1:C1", "指标定义、计算方法与解读"); metricsSheet.getRange("A3:C3").values = [["指标", "计算公式", "结果代表什么"]]; header(metricsSheet.getRange("A3:C3")); metricsSheet.getRangeByIndexes(3, 0, metricRows.length, 3).values = metricRows; body(metricsSheet.getRange("A4:C11")); table(metricsSheet, "A3:C11", "MetricDefinitionsTable"); metricsSheet.getRange("A:A").format.columnWidth = 20; metricsSheet.getRange("B:B").format.columnWidth = 55; metricsSheet.getRange("C:C").format.columnWidth = 55; metricsSheet.getRange("A4:C11").format.wrapText = true; metricsSheet.getRange("A4:C11").format.autofitRows();

const check = await workbook.inspect({ kind: "table", range: "评测总览!A1:P14", include: "values,formulas", tableMaxRows: 14, tableMaxCols: 16 });
console.log(check.ndjson);
const errors = await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 100 }, summary: "formula errors" });
console.log(errors.ndjson);
if (previewDir) {
  await fs.mkdir(previewDir, { recursive: true });
  for (const sheet of [overview, casesSheet, papersSheet, goldSheet, exceptionsSheet, metricsSheet]) {
    const preview = await workbook.render({ sheetName: sheet.name, autoCrop: "all", scale: 1, format: "png" });
    await fs.writeFile(path.join(previewDir, `${sheet.name}.png`), new Uint8Array(await preview.arrayBuffer()));
  }
}
await fs.mkdir(path.dirname(outputPath), { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(`Saved ${outputPath}`);
