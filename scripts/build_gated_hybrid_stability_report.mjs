import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const [stabilityPath, beforePath, afterPath, outputPath, previewDir] = process.argv.slice(2);
const stability = JSON.parse(await fs.readFile(stabilityPath, "utf8"));
const before = JSON.parse(await fs.readFile(beforePath, "utf8"));
const after = JSON.parse(await fs.readFile(afterPath, "utf8"));
const wb = Workbook.create();
const navy="#17365D", green="#E2F0D9", yellow="#FFF2CC";
function title(sheet, range, value){sheet.getRange(range).merge();sheet.getRange(range.split(":")[0]).values=[[value]];sheet.getRange(range).format={fill:navy,font:{bold:true,color:"#FFFFFF",size:16},rowHeight:30};sheet.showGridLines=false;}
function head(range){range.format={fill:navy,font:{bold:true,color:"#FFFFFF"},horizontalAlignment:"center",wrapText:true};}

const overview=wb.worksheets.add("阶段结论");title(overview,"A1:F1","门控 Hybrid 执行复用与三进程稳定性");
overview.getRange("A3:F3").values=[["检查项","结果","门槛","判定","作用","生产影响"]];head(overview.getRange("A3:F3"));
overview.getRange("A4:F11").values=[
 ["Dense 调用次数",1,"每查询一次",true,"复用门控阶段排名","消除重复向量编码"],
 ["独立进程数",stability.run_count,3,stability.run_count>=3,"排除单次偶然结果","无"],
 ["质量与排序一致",stability.quality_equal&&stability.top5_rankings_equal&&stability.scores_equal,true,stability.quality_equal&&stability.top5_rankings_equal&&stability.scores_equal,"证明只优化执行成本","无质量回归"],
 ["路由一致",stability.routes_equal,true,stability.routes_equal,"4/8 查询稳定触发 Hybrid","成本可预测"],
 ["平均延迟 CV",stability.timing.average_query_ms.cv,.5,stability.timing.average_query_ms.cv<=.5,"衡量跨进程相对波动","通过稳定性门槛"],
 ["P95 均值(ms)",stability.timing.p95_query_ms.mean,"记录",null,"观察尾延迟","较上一轮显著下降"],
 ["稳定性通过",stability.decision.stability_validated,true,stability.decision.stability_validated,"允许进入更大未见集验证","生产仍关闭"],
 ["生产默认",stability.decision.production_default,false,!stability.decision.production_default,"v2 仅 8 题","继续关闭"]
];
overview.getRange("B8:C8").format.numberFormat="0.00%";overview.getRange("A4:F11").format.wrapText=true;overview.getRange("A:A").format.columnWidth=25;overview.getRange("B:E").format.columnWidth=19;overview.getRange("F:F").format.columnWidth=38;
overview.getRange("A13:F15").merge();overview.getRange("A13").values=[["结论：复用门控阶段已经计算的 Dense 排名后，质量、Top-5、分数和路由完全不变；三次独立进程平均查询延迟 CV=10.67%，稳定性通过。当前证据仍只有 8 个未见问题，因此不启用生产默认，下一步扩大未见评测集。"]];overview.getRange("A13:F15").format={fill:green,font:{bold:true},wrapText:true,verticalAlignment:"center"};

const timing=wb.worksheets.add("三次原始耗时");title(timing,"A1:F1","三次独立进程原始耗时与 CV");timing.getRange("A3:F3").values=[["指标","运行1(ms)","运行2(ms)","运行3(ms)","均值(ms)","CV"]];head(timing.getRange("A3:F3"));
timing.getRange("A4:F5").values=[["平均查询",...stability.timing.average_query_ms.values,stability.timing.average_query_ms.mean,stability.timing.average_query_ms.cv],["P95 查询",...stability.timing.p95_query_ms.values,stability.timing.p95_query_ms.mean,stability.timing.p95_query_ms.cv]];timing.getRange("B4:E5").format.numberFormat="0.000";timing.getRange("F4:F5").format.numberFormat="0.00%";timing.getRange("A:F").format.columnWidth=23;
timing.getRange("A7:F10").merge();timing.getRange("A7").values=[["CV = 三次独立进程耗时的总体标准差 ÷ 平均值。当前晋升门槛只要求平均查询 CV≤50%；P95 CV 作为尾延迟观察项记录，不单独阻断。每次进程均执行固定两次、不计入正式耗时的预热查询。"]];timing.getRange("A7:F10").format={fill:yellow,wrapText:true,verticalAlignment:"center"};

const compare=wb.worksheets.add("优化前后等价性");title(compare,"A1:F1","重复 Dense 消除前后对比");compare.getRange("A3:F3").values=[["项目","优化前","优化后运行1","变化","判定","解释"]];head(compare.getRange("A3:F3"));
const b=before.gated_hybrid.summary,a=after.gated_hybrid.summary;
compare.getRange("A4:F10").values=[
 ["Recall@5",b.recall_at_5,a.recall_at_5,a.recall_at_5-b.recall_at_5,true,"证据覆盖不变"],
 ["MRR@5",b.mrr_at_5,a.mrr_at_5,a.mrr_at_5-b.mrr_at_5,true,"首个相关证据名次不变"],
 ["nDCG@5",b.ndcg_at_5,a.ndcg_at_5,a.ndcg_at_5-b.ndcg_at_5,true,"排序质量不变"],
 ["Top-5 排名", "基准", "完全一致", null, stability.top5_rankings_equal,"逐题 Chunk 顺序相同"],
 ["RRF 分数", "基准", "完全一致", null, stability.scores_equal,"融合数学结果相同"],
 ["平均查询(ms)",b.average_query_latency_ms,a.average_query_latency_ms,a.average_query_latency_ms-b.average_query_latency_ms,null,"历史单次环境差异较大，仅作参考"],
 ["P95(ms)",b.p95_query_latency_ms,a.p95_query_latency_ms,a.p95_query_latency_ms-b.p95_query_latency_ms,null,"以三进程稳定性数据作为正式性能证据"]
];compare.getRange("B4:D6").format.numberFormat="0.00%";compare.getRange("B9:D10").format.numberFormat="0.000";compare.getRange("A4:F10").format.wrapText=true;compare.getRange("A:A").format.columnWidth=24;compare.getRange("B:E").format.columnWidth=20;compare.getRange("F:F").format.columnWidth=44;

const protocol=wb.worksheets.add("测试口径与下一步");title(protocol,"A1:D1","测试逻辑、结果含义与后续计划");protocol.getRange("A3:D3").values=[["测试","具体作用","通过代表什么","失败代表什么"]];head(protocol.getRange("A3:D3"));protocol.getRange("A4:D8").values=[
 ["Dense 单次调用测试","统计触发 Hybrid 时 Dense/BM25 调用次数","没有重复向量编码","重复 Dense 会增加平均和尾延迟"],
 ["质量等价测试","逐项比较 Recall/MRR/nDCG、Top-5 和分数","执行优化未改变结果","不能把速度收益建立在质量变化上"],
 ["路由一致测试","比较三进程每题 Dense/Hybrid 决策","门控成本与行为可复现","相同问题可能走不同路径"],
 ["延迟稳定测试","计算三次平均查询延迟 CV","跨进程波动在预声明范围内","性能收益可能只是偶然"],
 ["下一步","冻结阈值，扩大未见问题集","增强泛化证据后再评估生产晋升","禁止使用 v2 继续调阈值"]
];protocol.getRange("A4:D8").format.wrapText=true;protocol.getRange("A:A").format.columnWidth=28;protocol.getRange("B:D").format.columnWidth=48;

for(const sheet of wb.worksheets.items){const used=sheet.getUsedRange();used.format.font={name:"Microsoft YaHei",size:10};}
await fs.mkdir(previewDir,{recursive:true});
for(const sheet of wb.worksheets.items){const png=await wb.render({sheetName:sheet.name,autoCrop:"all",scale:1,format:"png"});await fs.writeFile(`${previewDir}/${sheet.name}.png`,new Uint8Array(await png.arrayBuffer()));}
console.log((await wb.inspect({kind:"table",range:"阶段结论!A1:F15",include:"values,formulas",tableMaxRows:20,tableMaxCols:8})).ndjson);
console.log((await wb.inspect({kind:"match",searchTerm:"#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",options:{useRegex:true,maxResults:50},summary:"公式错误扫描"})).ndjson);
await fs.mkdir(path.dirname(outputPath),{recursive:true});const out=await SpreadsheetFile.exportXlsx(wb);await out.save(outputPath);
