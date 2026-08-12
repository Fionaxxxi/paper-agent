import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const [inputPath, outputPath, previewDir] = process.argv.slice(2);
if (!inputPath || !outputPath || !previewDir) throw new Error("Usage: node build_local_rag_report.mjs input.json output.xlsx previewDir");
const report = JSON.parse(await fs.readFile(inputPath, "utf8"));
const { summary: s, config: c, cases } = report;
const wb = Workbook.create(), navy = "#1B3B63", blue = "#DDEBF7", green = "#E2F0D9", yellow = "#FFF2CC", red = "#FCE4D6";
function title(sh, range, text) { sh.getRange(range).merge(); sh.getRange(range.split(":")[0]).values = [[text]]; sh.getRange(range).format = { fill: navy, font: { bold: true, color: "#FFFFFF", size: 16 }, rowHeight: 28 }; sh.showGridLines = false; }
function header(range) { range.format = { fill: navy, font: { bold: true, color: "#FFFFFF" }, horizontalAlignment: "center", wrapText: true }; }

const overview = wb.worksheets.add("基线总览"); title(overview, "A1:I1", "PaperAgent 本地 RAG：BM25 全文检索基线");
overview.getRange("A3:I3").values = [["问题数", "Chunk数", "Recall@1", "Recall@3", "Recall@5", "MRR@5", "nDCG@5", "平均延迟ms", "P95延迟ms"]]; header(overview.getRange("A3:I3"));
overview.getRange("A4:I4").values = [[s.case_count, s.chunk_count, s.recall_at_1, s.recall_at_3, s.recall_at_5, s.mrr_at_5, s.ndcg_at_5, s.average_query_latency_ms, s.p95_query_latency_ms]];
overview.getRange("C4:G4").format.numberFormat = "0.00%"; overview.getRange("H4:I4").format.numberFormat = "0.000";
overview.getRange("A6:I6").merge(); overview.getRange("A6").values = [["结论：这是未做查询翻译、向量化或 LLM 改写的纯词法下限基线。Recall@5 为 18.75%，说明中文问题与英文全文之间存在明显词汇鸿沟。"]]; overview.getRange("A6:I6").format = { fill: yellow, font: { bold: true }, wrapText: true, rowHeight: 38 };
overview.getRange("A8:I8").merge(); overview.getRange("A8").values = [["下一步：先增加确定性的中英术语查询改写对照，再实现 Dense；所有候选必须使用同一语料、金标准和 Chunker，报告逐题净提升与回归。"]]; overview.getRange("A8:I8").format = { fill: blue, wrapText: true, rowHeight: 38 }; overview.getRange("A:I").format.columnWidth = 18;

const detail = wb.worksheets.add("逐题指标"); title(detail, "A1:M1", "16 题逐题检索指标");
detail.getRange("A3:M3").values = [["用例", "问题", "类别", "难度", "首个相关排名", "Recall@1", "Recall@3", "Recall@5", "MRR@5", "nDCG@5", "延迟ms", "金标准Chunk", "状态"]]; header(detail.getRange("A3:M3"));
const detailRows = cases.map(x => [x.id, x.question, x.category, x.difficulty, x.first_relevant_rank, x.metrics.recall_at_1, x.metrics.recall_at_3, x.metrics.recall_at_5, x.metrics.mrr_at_5, x.metrics.ndcg_at_5, x.latency_ms, x.relevant_chunk_ids.join("; "), x.metrics.recall_at_5 > 0 ? "Top5命中" : "Top5未命中"]);
detail.getRangeByIndexes(3, 0, detailRows.length, 13).values = detailRows; detail.getRange(`F4:J${detailRows.length + 3}`).format.numberFormat = "0.00%"; detail.getRange(`K4:K${detailRows.length + 3}`).format.numberFormat = "0.000"; detail.getRange(`A4:M${detailRows.length + 3}`).format.wrapText = true; detail.getRange("A:A").format.columnWidth = 22; detail.getRange("B:B").format.columnWidth = 48; detail.getRange("L:L").format.columnWidth = 28; detail.getRange("M:M").format.columnWidth = 16; detail.freezePanes.freezeRows(3);

const ranks = wb.worksheets.add("Top5排名"); title(ranks, "A1:I1", "每题 Top-5 原始排名与证据预览"); ranks.getRange("A3:I3").values = [["用例", "排名", "Chunk", "论文", "PDF页", "BM25分数", "是否金标准", "问题", "文本预览"]]; header(ranks.getRange("A3:I3"));
const rankRows = cases.flatMap(x => x.results.map(r => [x.id, r.rank, r.chunk_id, r.document_id, r.page, r.score, r.is_relevant, x.question, r.text_preview])); ranks.getRangeByIndexes(3, 0, rankRows.length, 9).values = rankRows; ranks.getRange(`A4:I${rankRows.length + 3}`).format.wrapText = true; ranks.getRange("A:A").format.columnWidth = 22; ranks.getRange("C:D").format.columnWidth = 28; ranks.getRange("H:H").format.columnWidth = 42; ranks.getRange("I:I").format.columnWidth = 55; ranks.freezePanes.freezeRows(3);

const method = wb.worksheets.add("配置与口径"); title(method, "A1:D1", "技术配置、指标口径与实验边界"); method.getRange("A3:D3").values = [["项目", "值/计算方法", "作用", "边界"]]; header(method.getRange("A3:D3"));
method.getRange("A4:D14").values = [["配置ID", c.config_id, "固定实验身份", "不同配置必须使用新 ID"], ["检索器", c.retriever_family, "纯 Sparse BM25", "没有向量或图索引"], ["分词器", c.tokenizer, "英文词 + 中文单字/双字", "不是语义跨语言模型"], ["参数", `k1=${c.k1}; b=${c.b}`, "BM25 词频与长度归一化", "未针对金标准调参"], ["LLM调用", c.llm_calls, "确认无生成成本", "只测检索"], ["Recall@K", "Top-K 命中的不同金标准 Chunk 数 ÷ 金标准 Chunk 数", "衡量证据召回", "精确 Chunk 命中"], ["MRR@K", "第一条金标准 Chunk 排名的倒数", "衡量首次命中位置", "未命中为 0"], ["nDCG@K", "DCG@K ÷ 理想 DCG@K", "衡量位置折损", "当前证据均为同等级"], ["延迟", "单问题 search 墙钟时间", "观察本地检索开销", "不含 PDF 解析和索引构建"], ["数据集", `gold=${report.dataset_version}; corpus=${report.corpus_version}`, "冻结评测输入", "不得看结果后改金标准"], ["索引构建", `${s.index_build_ms} ms`, "1098 Chunk 建立内存索引", "当前未落盘持久化"]]; method.getRange("A4:D14").format = { wrapText: true, borders: { preset: "inside", style: "thin", color: "#D9E2F3" } }; method.getRange("A:A").format.columnWidth = 22; method.getRange("B:B").format.columnWidth = 52; method.getRange("C:D").format.columnWidth = 34;

for (const sheet of wb.worksheets.items) sheet.getUsedRange().format.font = { name: "Microsoft YaHei" };
detail.getRange(`M4:M${detailRows.length + 3}`).conditionalFormats.add("containsText", { text: "Top5命中", format: { fill: green } }); detail.getRange(`M4:M${detailRows.length + 3}`).conditionalFormats.add("containsText", { text: "Top5未命中", format: { fill: red } });
await fs.mkdir(previewDir, { recursive: true }); for (const sheet of wb.worksheets.items) { const png = await wb.render({ sheetName: sheet.name, autoCrop: "all", scale: 1, format: "png" }); await fs.writeFile(path.join(previewDir, `${sheet.name}.png`), new Uint8Array(await png.arrayBuffer())); }
console.log((await wb.inspect({ kind: "table", range: "基线总览!A1:I8", include: "values,formulas", tableMaxRows: 10, tableMaxCols: 10 })).ndjson); console.log((await wb.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 100 } })).ndjson);
await fs.mkdir(path.dirname(outputPath), { recursive: true }); const output = await SpreadsheetFile.exportXlsx(wb); await output.save(outputPath); console.log(outputPath);
