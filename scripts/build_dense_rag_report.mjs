import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const [input, output, previewDir] = process.argv.slice(2);
if (!input || !output || !previewDir) throw new Error("用法: node build_dense_rag_report.mjs 输入JSON 输出XLSX 预览目录");
const report = JSON.parse(await fs.readFile(input, "utf8"));
const wb = Workbook.create();
const navy = "#17365D", blue = "#D9EAF7", green = "#E2F0D9", yellow = "#FFF2CC", red = "#FCE4D6", gray = "#E7E6E6";
const metricNames = {recall_at_1:"Chunk Recall@1",recall_at_3:"Chunk Recall@3",recall_at_5:"Chunk Recall@5",mrr_at_5:"MRR@5",ndcg_at_5:"nDCG@5",page_recall_at_5:"Page Recall@5",page_ndcg_at_5:"Page nDCG@5"};
function title(sheet, range, text) { sheet.getRange(range).merge(); const c = sheet.getRange(range.split(":")[0]); c.values=[[text]]; c.format={fill:navy,font:{bold:true,color:"#FFFFFF",size:16},rowHeight:30}; sheet.showGridLines=false; }
function header(range) { range.format={fill:navy,font:{bold:true,color:"#FFFFFF"},horizontalAlignment:"center",verticalAlignment:"center",wrapText:true,borders:{preset:"outside",style:"thin",color:navy}}; }

const summary = wb.worksheets.add("结果总览");
title(summary,"A1:J1","多语言 Dense Retrieval 与 BM25 对比");
summary.getRange("A3:J3").values=[["数据集","检索器","Recall@1","Recall@3","Recall@5","MRR@5","nDCG@5","Page Recall@5","Page nDCG@5","平均查询延迟(ms)"]]; header(summary.getRange("A3:J3"));
const summaryRows=[];
for (const [key,label] of [["development","开发集（16题）"],["holdout","独立保留集（10题）"]]) {
  const c=report.comparisons[key];
  for (const engine of ["bm25","dense"]) summaryRows.push([label,engine==="bm25"?"BM25":"Dense",...Object.keys(metricNames).map(m=>c.metrics[m][engine]),engine==="bm25"?c.bm25_latency_ms:c.dense_latency_ms]);
}
summary.getRange("A4:J7").values=summaryRows; summary.getRange("C4:I7").format.numberFormat="0.00%"; summary.getRange("J4:J7").format.numberFormat="0.00";
summary.getRange("A9:D9").values=[["关键结论","BM25","Dense","变化"]]; header(summary.getRange("A9:D9"));
const hold=report.comparisons.holdout;
summary.getRange("A10:D13").values=[
  ["保留集 Recall@5",hold.metrics.recall_at_5.bm25,hold.metrics.recall_at_5.dense,hold.metrics.recall_at_5.delta],
  ["保留集 nDCG@5",hold.metrics.ndcg_at_5.bm25,hold.metrics.ndcg_at_5.dense,hold.metrics.ndcg_at_5.delta],
  ["逐题改善 / 回归",hold.outcomes.improved,hold.outcomes.regressed,hold.outcomes.unchanged],
  ["生产默认",true,report.decision.production_default,"Dense 未开启"]
]; summary.getRange("B10:D11").format.numberFormat="0.00%";
summary.getRange("F9:J9").merge(); summary.getRange("F9").values=[["晋升判定"]]; summary.getRange("F9:J9").format={fill:navy,font:{bold:true,color:"#FFFFFF"}};
summary.getRange("F10:J11").merge(); summary.getRange("F10").values=[[report.decision.reason]]; summary.getRange("F10:J11").format={fill:yellow,font:{bold:true},wrapText:true,verticalAlignment:"center"};
summary.getRange("F13:J15").merge(); summary.getRange("F13").values=[["解释：Dense 能跨越中文问题与英文论文的词汇差异，使保留集 Recall@5 提升 20 个百分点；但仍有 3 题排序回归，且查询和首次索引成本明显高于 BM25，因此只保留为下一轮实验候选。"]]; summary.getRange("F13:J15").format={fill:blue,wrapText:true,verticalAlignment:"center"};
summary.getRange("A:J").format.columnWidth=18; summary.getRange("A:A").format.columnWidth=24; summary.getRange("F:J").format.columnWidth=19;

const metrics=wb.worksheets.add("指标对比"); title(metrics,"A1:G1","指标定义与数据集对比");
metrics.getRange("A3:G3").values=[["数据集","指标","BM25","Dense","绝对变化","指标含义","如何计算"]]; header(metrics.getRange("A3:G3"));
const meanings={recall_at_1:"Top-1 是否命中精确金标准 Chunk",recall_at_3:"Top-3 是否命中精确金标准 Chunk",recall_at_5:"Top-5 是否命中精确金标准 Chunk",mrr_at_5:"首次命中排名的倒数均值",ndcg_at_5:"考虑命中位置折损的排序质量",page_recall_at_5:"Top-5 是否命中金标准页",page_ndcg_at_5:"按页去重后的排序质量"};
const formulas={recall_at_1:"命中题数 ÷ 总题数（K=1）",recall_at_3:"命中题数 ÷ 总题数（K=3）",recall_at_5:"命中题数 ÷ 总题数（K=5）",mrr_at_5:"平均(首次命中则 1/排名，否则 0)",ndcg_at_5:"平均(DCG@5 ÷ 理想DCG@5)",page_recall_at_5:"命中证据页题数 ÷ 总题数",page_ndcg_at_5:"同页只计一次后计算 nDCG@5"};
const metricRows=[]; for(const [key,label] of [["development","开发集"],["holdout","独立保留集"]]) for(const m of Object.keys(metricNames)){const x=report.comparisons[key].metrics[m];metricRows.push([label,metricNames[m],x.bm25,x.dense,x.delta,meanings[m],formulas[m]]);}
metrics.getRangeByIndexes(3,0,metricRows.length,7).values=metricRows; metrics.getRange(`C4:E${metricRows.length+3}`).format.numberFormat="0.00%"; metrics.getRange(`A4:G${metricRows.length+3}`).format.wrapText=true; metrics.getRange("A:B").format.columnWidth=22; metrics.getRange("C:E").format.columnWidth=14; metrics.getRange("F:G").format.columnWidth=42; metrics.freezePanes.freezeRows(3);

const cases=wb.worksheets.add("逐题结果"); title(cases,"A1:H1","开发集与独立保留集逐题排序变化");
cases.getRange("A3:H3").values=[["数据集","用例ID","BM25首次命中","Dense首次命中","Recall@5变化","nDCG@5变化","结果","结果代表什么"]]; header(cases.getRange("A3:H3"));
const caseRows=[]; for(const [key,label] of [["development","开发集"],["holdout","独立保留集"]]) for(const x of report.comparisons[key].cases) caseRows.push([label,x.id,x.bm25_first_rank||"未命中",x.dense_first_rank||"未命中",x.recall_delta,x.ndcg_delta,x.outcome,x.outcome==="improved"?"正确证据进入 Top-5 或排名上升":x.outcome==="regressed"?"正确证据掉出 Top-5 或排名下降":"主排序质量没有变化"]);
cases.getRangeByIndexes(3,0,caseRows.length,8).values=caseRows; cases.getRange(`E4:F${caseRows.length+3}`).format.numberFormat="0.00%"; cases.getRange(`A4:H${caseRows.length+3}`).format.wrapText=true; cases.getRange("A:A").format.columnWidth=16; cases.getRange("B:B").format.columnWidth=34; cases.getRange("C:G").format.columnWidth=16; cases.getRange("H:H").format.columnWidth=42; cases.freezePanes.freezeRows(3); cases.getRange(`G4:G${caseRows.length+3}`).conditionalFormats.add("containsText",{text:"regressed",format:{fill:red}}); cases.getRange(`G4:G${caseRows.length+3}`).conditionalFormats.add("containsText",{text:"improved",format:{fill:green}});

const config=wb.worksheets.add("配置与成本"); title(config,"A1:D1","Dense 实验配置、成本与复现信息");
config.getRange("A3:D3").values=[["类别","配置项","值","说明"]]; header(config.getRange("A3:D3"));
const cfg=report.dense_config, timing=report.dense_timing;
config.getRange("A4:D18").values=[
 ["模型","模型",cfg.model,"首个轻量多语言候选，不代表最终选型"],["模型","向量维度",cfg.dimension,"每个 Chunk 的浮点向量长度"],["模型","最大 token",cfg.max_tokens,"超过长度由模型截断"],["运行时","推理",cfg.runtime,"CPU ONNX，不安装 PyTorch"],["运行时","FastEmbed",cfg.fastembed_version,"本轮实际运行版本"],["相似度","池化",cfg.pooling,"FastEmbed 0.7.4 的均值池化"],["相似度","归一化",cfg.similarity,"显式 L2 归一化后做余弦相似度"],["输入","查询前缀",cfg.query_prefix,"模型未要求 query/document 指令前缀"],["输入","文档前缀",cfg.document_prefix,"模型未要求 query/document 指令前缀"],["批处理","batch size",cfg.batch_size,"构建 1098 Chunk 向量时使用"],["成本","LLM 调用",cfg.llm_calls,"纯 Embedding 评测"],["耗时","模型加载(ms)",timing.model_load_ms,"首次加载模型"],["耗时","索引构建(ms)",timing.index_build_ms,"当前每次运行重新编码，尚未持久化缓存"],["来源","FastEmbed 支持模型","https://qdrant.github.io/fastembed/examples/Supported_Models/","模型维度、语言与输入长度来源"],["来源","模型卡","https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2","模型许可和用途来源"]];
config.getRange("A4:D18").format.wrapText=true; config.getRange("A:A").format.columnWidth=16; config.getRange("B:B").format.columnWidth=24; config.getRange("C:C").format.columnWidth=64; config.getRange("D:D").format.columnWidth=46;

const decision=wb.worksheets.add("决策与下一步"); title(decision,"A1:D1","技术决策与下一轮单变量实验");
decision.getRange("A3:D3").values=[["判断项","本轮证据","结论","下一步"]]; header(decision.getRange("A3:D3"));
decision.getRange("A4:D9").values=[
 ["语义泛化","保留集 Recall@5 60% → 80%，nDCG@5 46.93% → 59.05%","Dense 有真实收益","重复运行并增加第二个多语言模型"],
 ["稳定性","保留集 4 提升、3 回归、3 不变","尚不稳定","分析 LightRAG、ReAct、ToolFormer 回归"],
 ["速度","Dense 334.54ms；BM25 14.39ms","约 23 倍查询延迟","持久化向量索引，区分冷启动与热查询"],
 ["生产状态","自动判定 promote_to_candidate=false","继续关闭","只有通过质量、稳定性和延迟闸门才晋升"],
 ["选型原则","当前模型只是第一候选","不写死实现","相同语料、标注与指标对照其他 Dense / Hybrid"],
 ["推荐顺序","缓存索引 → 重复性测试 → 第二 Dense → Hybrid","一次只改变一个变量","保留逐题回归和 Excel 历史"]];
decision.getRange("A4:D9").format={wrapText:true,borders:{preset:"inside",style:"thin",color:gray}}; decision.getRange("A:A").format.columnWidth=22; decision.getRange("B:D").format.columnWidth=47;

for (const sheet of wb.worksheets.items) sheet.getUsedRange().format.font={name:"Microsoft YaHei",size:10};
await fs.mkdir(previewDir,{recursive:true});
for (const sheet of wb.worksheets.items) { const p=await wb.render({sheetName:sheet.name,autoCrop:"all",scale:1,format:"png"}); await fs.writeFile(path.join(previewDir,`${sheet.name}.png`),new Uint8Array(await p.arrayBuffer())); }
console.log((await wb.inspect({kind:"table",range:"结果总览!A1:J15",include:"values,formulas",tableMaxRows:20,tableMaxCols:12})).ndjson);
console.log((await wb.inspect({kind:"match",searchTerm:"#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",options:{useRegex:true,maxResults:100},summary:"最终公式错误扫描"})).ndjson);
await fs.mkdir(path.dirname(output),{recursive:true}); const xlsx=await SpreadsheetFile.exportXlsx(wb); await xlsx.save(output); console.log(output);
