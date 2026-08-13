import fs from "node:fs/promises";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const [beforePath, afterPath, comparePath, outputPath, previewDir] = process.argv.slice(2);
if (!previewDir) throw new Error("用法: node build_mpnet_warmup_report.mjs before after compare output preview");
const before=JSON.parse(await fs.readFile(beforePath,"utf8")),after=JSON.parse(await fs.readFile(afterPath,"utf8")),comparison=JSON.parse(await fs.readFile(comparePath,"utf8"));
const wb=Workbook.create(),navy="#1D3D64",blue="#DCEAF7",green="#E2F0D9",yellow="#FFF2CC",red="#FCE4D6";
const title=(s,r,t)=>{s.getRange(r).merge();s.getRange(r.split(":")[0]).values=[[t]];s.getRange(r).format={fill:navy,font:{bold:true,color:"#FFFFFF",size:15},rowHeight:28,verticalAlignment:"center"};s.showGridLines=false;};
const head=r=>r.format={fill:navy,font:{bold:true,color:"#FFFFFF"},horizontalAlignment:"center",verticalAlignment:"center",wrapText:true};

const result=wb.worksheets.add("阶段结论");title(result,"A1:F1","MPNet 首次查询预热隔离实验");
result.getRange("A3:F3").values=[["检查项","预热前","预热后","门槛","判定","说明"]];head(result.getRange("A3:F3"));
result.getRange("A4:F10").values=[
 ["固定预热协议","无","2次",2,true,"固定中性英文查询，不使用测试题"],
 ["预热计入正式延迟","是","否",false,true,"逐次记录但从开发/保留集计时中排除"],
 ["开发集平均查询CV",before.timing.development_average_query_ms.cv,after.timing.development_average_query_ms.cv,.5,after.timing.development_average_query_ms.cv<=.5,"波动显著下降"],
 ["保留集平均查询CV",before.timing.holdout_average_query_ms.cv,after.timing.holdout_average_query_ms.cv,.5,after.timing.holdout_average_query_ms.cv<=.5,"52.25% 降至 28.50%"],
 ["质量/Top-5/分数",true,comparison.quality_preserved,true,comparison.quality_preserved,"预热未改变检索结果"],
 ["稳定性通过",before.decision.stability_validated,after.decision.stability_validated,true,after.decision.stability_validated,"首次初始化解释上轮失败"],
 ["生产默认",false,false,false,true,"通过稳定性不等于生产晋升"]];
result.getRange("B6:E7").format.numberFormat="0.00%";result.getRange("A4:F10").format.wrapText=true;result.getRange("A:A").format.columnWidth=28;result.getRange("B:E").format.columnWidth=18;result.getRange("F:F").format.columnWidth=42;
result.getRange("A12:F14").merge();result.getRange("A12").values=[["结论：固定两次不计时预热后，保留集平均查询 CV 从 52.25% 降到 28.50%，开发集从 35.63% 降到 15.58%；质量、Top-5 与分数保持一致。MPNet 稳定性通过，生产仍关闭，下一步进入 Dense + BM25 Hybrid 单变量互补实验。"]];result.getRange("A12:F14").format={fill:green,font:{bold:true},wrapText:true,verticalAlignment:"center"};

const raw=wb.worksheets.add("三次原始数据");title(raw,"A1:H1","预热后独立进程原始测量");raw.getRange("A3:H3").values=[["运行","预热1(ms)","预热2(ms)","开发平均(ms)","开发P95(ms)","保留平均(ms)","保留P95(ms)","缓存命中"]];head(raw.getRange("A3:H3"));
const rows=after.warmup_runs.map((w,i)=>[i+1,...w.latency_ms,after.timing.development_average_query_ms.values[i],after.timing.development_p95_query_ms.values[i],after.timing.holdout_average_query_ms.values[i],after.timing.holdout_p95_query_ms.values[i],after.all_cache_hits]);raw.getRangeByIndexes(3,0,rows.length,8).values=rows;raw.getRange("B4:G6").format.numberFormat="0.000";raw.getRange("A:H").format.columnWidth=21;raw.getRange("A8:H10").merge();raw.getRange("A8").values=[["原始数据完整保留：预热耗时只用于诊断，不参与正式平均延迟和 P95 计算。三次进程均重新加载模型，并命中 D:/langgraphproject/data/cache 下同一向量缓存指纹。"]];raw.getRange("A8:H10").format={fill:blue,wrapText:true,verticalAlignment:"center"};

const cmp=wb.worksheets.add("预热前后对比");title(cmp,"A1:G1","预热前后均值与变异系数变化");cmp.getRange("A3:G3").values=[["指标","预热前均值(ms)","预热后均值(ms)","均值变化","预热前CV","预热后CV","CV百分点变化"]];head(cmp.getRange("A3:G3"));
const labels={development_average_query_ms:"开发集平均查询",development_p95_query_ms:"开发集P95",holdout_average_query_ms:"保留集平均查询",holdout_p95_query_ms:"保留集P95"};const cr=Object.entries(labels).map(([k,l])=>{const x=comparison.metrics[k];return[l,x.before_mean_ms,x.after_mean_ms,x.mean_change_pct/100,x.before_cv,x.after_cv,x.cv_change_pct_points/100]});cmp.getRangeByIndexes(3,0,cr.length,7).values=cr;cmp.getRange("B4:C7").format.numberFormat="0.000";cmp.getRange("D4:G7").format.numberFormat="0.00%";cmp.getRange("A:G").format.columnWidth=23;cmp.getRange("A9:G11").merge();cmp.getRange("A9").values=[["解释：开发/保留集平均查询的均值和 CV 都明显下降；P95 CV 改善较小，说明系统仍有尾延迟，但当前稳定性闸门以两个数据集的平均查询 CV≤50% 和检索器构造<100ms为准。"]];cmp.getRange("A9:G11").format={fill:yellow,wrapText:true,verticalAlignment:"center"};

const protocol=wb.worksheets.add("协议与下一步");title(protocol,"A1:D1","冻结协议、计算口径与后续工作");protocol.getRange("A3:D3").values=[["项目","冻结规则","为什么这样做","后续影响"]];head(protocol.getRange("A3:D3"));protocol.getRange("A4:D11").values=[
 ["预热文本","academic paper semantic retrieval warmup","与正式测试题无关，避免泄漏","后续稳定性实验保持不变"],
 ["预热次数",2,"第一次触发初始化，第二次观察进入稳定态","不得事后修改次数"],
 ["计时边界","预热结束后才运行开发集和保留集","隔离 ONNX 首次推理开销","预热耗时仍逐次记录"],
 ["CV","总体标准差 ÷ 平均值","衡量跨独立进程的相对波动","平均查询 CV 必须≤50%"],
 ["质量约束","Recall/MRR/nDCG、Top-5 和分数完全一致","性能修正不得改变质量","任何差异均失败"],
 ["版本风险","FastEmbed 0.7.4 提示 MPNet 使用 mean pooling","升级依赖可能改变 Embedding 行为","锁版本并保留警告记录"],
 ["下一步","Dense + BM25 Hybrid 互补对照","用词法召回修复 RAG decoding 回归","一次只新增融合变量"],
 ["生产边界","继续关闭","稳定性通过尚未证明 Hybrid 净收益","评测通过后再决定"]];protocol.getRange("A4:D11").format.wrapText=true;protocol.getRange("A:A").format.columnWidth=24;protocol.getRange("B:D").format.columnWidth=48;

await fs.mkdir(previewDir,{recursive:true});for(const s of [result,raw,cmp,protocol]){const p=await wb.render({sheetName:s.name,autoCrop:"all",scale:1.5,format:"png"});await fs.writeFile(`${previewDir}/${s.name}.png`,new Uint8Array(await p.arrayBuffer()));}
console.log((await wb.inspect({kind:"table",sheetId:"阶段结论",range:"A1:F14",include:"values,formulas",tableMaxRows:20,tableMaxCols:8})).ndjson);
console.log((await wb.inspect({kind:"match",searchTerm:"#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",options:{useRegex:true,maxResults:100},summary:"公式错误扫描"})).ndjson);
await fs.mkdir(new URL(".",`file:///${outputPath.replaceAll("\\","/")}`).pathname,{recursive:true}).catch(()=>{});const file=await SpreadsheetFile.exportXlsx(wb);await file.save(outputPath);console.log(`Saved workbook: ${outputPath}`);
