$ErrorActionPreference = "Stop"
$python = "D:\miniconda3\envs\paper_agent\python.exe"
$report = "outputs\research_analyzer_prompt_ab\latest_analyzer_prompt_ab_online.json"
if (-not (Test-Path $python)) { throw "PaperAgent Python environment not found: $python" }
if (-not (Test-Path $report)) { throw "Real online A/B report not found: $report" }
& $python -m eval_harness.evolution_analyzer_ab $report
if ($LASTEXITCODE -ne 0) { throw "Real evolution promotion gate failed" }
Write-Host "Real report: outputs\evolution\real_analyzer_ab\latest_evolution_report.json"
