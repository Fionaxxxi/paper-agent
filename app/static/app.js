const $=id=>document.getElementById(id);let lastAnswer="";
const esc=value=>String(value??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
document.querySelectorAll("[data-query]").forEach(button=>button.onclick=()=>$("query").value=button.dataset.query);

async function health(){try{const response=await fetch("/health");if(!response.ok)throw new Error();$("mode").textContent="服务正常 · 可开始演示"}catch{$("mode").textContent="API 连接失败";document.querySelector(".status span").style.background="#ef4444"}}
function metric(label,value){return `<div class="metric"><small>${esc(label)}</small><b>${esc(value)}</b></div>`}
function render(data){const meta=data.paper_metadata||{},decision=meta.local_rag_decision||{},timings=data.node_timings||{},papers=data.papers||[];lastAnswer=data.answer||"";
  $("metrics").innerHTML=metric("任务类型",data.task_type||"qa")+metric("检索来源",meta.retrieval_source||"无检索")+metric("检索评分",Number(data.retrieval_score||0).toFixed(2))+metric("总耗时",`${timings.total??0}s`);
  $("answer").textContent=lastAnswer;$("paperCount").textContent=`${papers.length} 条证据`;$("traceId").textContent=data.trace_id||"";
  $("papers").innerHTML=papers.length?papers.map((p,i)=>`<article class="paper"><h3>${i+1}. ${esc(p.title||"未命名论文")}</h3><div class="paper-meta">${esc(p.source||"")} ${p.page?`· 第 ${p.page} 页`:""} ${p.chunk_id?`· ${esc(p.chunk_id)}`:""} ${p.retrieval_score!=null?`· ${Number(p.retrieval_score).toFixed(4)}`:""}</div><p>${esc(p.content||"")}</p></article>`).join(""):"<p>本次没有返回论文证据。</p>";
  $("route").innerHTML=decision.route?`本地门控选择 <strong>${esc(decision.route)}</strong><br><small>Top-1 ${Number(decision.dense_top1||0).toFixed(4)} · 间隔 ${Number(decision.dense_margin||0).toFixed(4)}</small>`:`检索策略：${esc(meta.ranking_strategy||meta.retrieval_mode||"本地短路")}`;
  const max=Math.max(...Object.values(timings).map(Number),.001);$("timings").innerHTML=Object.entries(timings).map(([name,value])=>`<div class="timing"><span>${esc(name)}<i><span style="width:${Math.max(3,Number(value)/max*100)}%"></span></i></span><b>${Number(value).toFixed(3)}s</b></div>`).join("");
  $("tools").innerHTML=(data.tools_used||[]).map(tool=>`<span class="chip">${esc(tool)}</span>`).join("")||'<span class="chip">无工具调用</span>';$("results").classList.remove("hidden");
}
$("submit").onclick=async()=>{const query=$("query").value.trim();if(!query)return;$("submit").disabled=true;$("requestStatus").textContent="LangGraph 正在执行…";try{const payload={query,conversation_id:$("conversation").value.trim()||null,pdf_path:$("pdf").value.trim()||null};const response=await fetch("/chat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});const result=await response.json();if(!response.ok)throw new Error(result.detail?.message||"请求失败");render(result.data);$("requestStatus").textContent="执行完成"}catch(error){$("requestStatus").textContent=`失败：${error.message}`}finally{$("submit").disabled=false}};
$("copy").onclick=async()=>{await navigator.clipboard.writeText(lastAnswer);$("copy").textContent="已复制";setTimeout(()=>$("copy").textContent="复制",1200)};
health();
