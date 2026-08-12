import fs from "node:fs/promises";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const input = process.argv[2] ?? "eval_harness/reports/parallel_multi_query_eval.json";
const output = process.argv[3] ?? "outputs/multi_query_replan/multi_query_replan_report.xlsx";
const previewDir = process.argv[4] ?? "outputs/multi_query_replan/previews";
const r = JSON.parse(await fs.readFile(input, "utf8"));
const wb = Workbook.create();
const navy = "#1B3B63", blue = "#DDEBF7", green = "#E2F0D9", yellow = "#FFF2CC";
function title(s, range, text) { s.getRange(range).merge(); s.getRange(range.split(":")[0]).values=[[text]]; s.getRange(range).format={fill:navy,font:{bold:true,color:"#FFFFFF",size:16},rowHeight:28}; s.showGridLines=false; }
function header(range) { range.format={fill:navy,font:{bold:true,color:"#FFFFFF"},horizontalAlignment:"center",borders:{preset:"inside",style:"thin",color:"#FFFFFF"}}; }

const overview=wb.worksheets.add("阶段总览");
title(overview,"A1:H1","PaperAgent 子查询并行验收与 Replan v1");
overview.getRange("A3:H3").values=[["重复次数","子查询数","串行中位(s)","并行中位(s)","加速","延迟下降","结果一致","阶段门槛"]]; header(overview.getRange("A3:H3"));
overview.getRange("A4:H4").values=[[r.repetitions,r.sub_query_count,r.serial_median_seconds,r.parallel_median_seconds,r.speedup,r.latency_reduction_pct/100,r.result_equality_rate,r.acceptance_passed?"通过":"不通过"]];
overview.getRange("C4:G4").format.numberFormat=[["0.000","0.000","0.00x","0.0%","0.0%"]];
overview.getRange("A6:H6").merge(); overview.getRange("A6").values=[["并行结论：达到止损门槛，结果和规划顺序保持 100% 一致；本阶段收口，不继续微调 worker。"]]; overview.getRange("A6:H6").format={fill:green,font:{bold:true},wrapText:true,rowHeight:32};
overview.getRange("A8:H8").merge(); overview.getRange("A8").values=[["下一阶段：已开始 Retrieval Replan v1，以失败类型选择受限动作，并保留最多一次重试预算。"]]; overview.getRange("A8:H8").format={fill:blue,font:{bold:true},wrapText:true,rowHeight:32}; overview.getRange("A:H").format.columnWidth=18;

const raw=wb.worksheets.add("重复实验"); title(raw,"A1:C1","子查询串行与并行重复延迟"); raw.getRange("A3:C3").values=[["轮次","串行耗时(s)","并行耗时(s)"]]; header(raw.getRange("A3:C3"));
raw.getRangeByIndexes(3,0,r.repetitions,3).values=r.serial_runs_seconds.map((v,i)=>[i+1,v,r.parallel_runs_seconds[i]]); raw.getRange(`B4:C${3+r.repetitions}`).format.numberFormat="0.000"; raw.getRange("A:C").format.columnWidth=22;

const actions=wb.worksheets.add("Replan动作"); title(actions,"A1:E1","Retrieval Replan v1 失败分类与动作边界"); actions.getRange("A3:E3").values=[["失败类型","判断依据","动作","查询变化","边界"]]; header(actions.getRange("A3:E3"));
actions.getRange("A4:E6").values=[
 ["暂时工具失败","TIMEOUT / NETWORK_ERROR / RATE_LIMITED / EXECUTION_ERROR","原查询重试","不改写","最多一次，不把网络故障误判为语义问题"],
 ["零结果","documents 为空且无暂时工具错误","放宽查询","移除引号括号，追加 research survey","确定性规则，不调用 LLM"],
 ["低相关","有文档但评分低于路由门槛","扩展上下文","追加 survey review","新 retry_query 覆盖旧 sub_queries"],
 ]; actions.getRange("A4:E6").format={wrapText:true,borders:{preset:"inside",style:"thin",color:"#D9E2F3"}}; actions.getRange("A:E").format.columnWidth=30; actions.getRange("B:B").format.columnWidth=45; actions.getRange("E:E").format.columnWidth=42;
actions.getRange("A8:E8").merge(); actions.getRange("A8").values=[["当前不是 Reflexion：不生成自由文本反思、不写长期记忆，只执行一次受控检索修复。下一步评测恢复率、无效重试率和分类准确率。"]]; actions.getRange("A8:E8").format={fill:yellow,wrapText:true,rowHeight:36};

for(const name of ["阶段总览","重复实验","Replan动作"]){wb.worksheets.getItem(name).getUsedRange().format.font={name:"Microsoft YaHei"};}
await fs.mkdir(previewDir,{recursive:true}); for(const name of ["阶段总览","重复实验","Replan动作"]){const p=await wb.render({sheetName:name,autoCrop:"all",scale:1,format:"png"});await fs.writeFile(`${previewDir}/${name}.png`,new Uint8Array(await p.arrayBuffer()));}
console.log((await wb.inspect({kind:"table",range:"阶段总览!A1:H8",include:"values,formulas",tableMaxRows:10,tableMaxCols:10})).ndjson);
console.log((await wb.inspect({kind:"match",searchTerm:"#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",options:{useRegex:true,maxResults:100}})).ndjson);
await fs.mkdir(output.split(/[\\/]/).slice(0,-1).join("/"),{recursive:true}); const x=await SpreadsheetFile.exportXlsx(wb); await x.save(output); console.log(output);
