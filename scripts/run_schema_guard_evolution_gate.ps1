$ErrorActionPreference = "Stop"
$python = "D:\miniconda3\envs\paper_agent\python.exe"
$report = "outputs\research_analyzer_prompt_ab\schema_guard\latest_analyzer_prompt_ab_online.json"
if (-not (Test-Path $python)) { throw "PaperAgent Python environment not found: $python" }
if (-not (Test-Path $report)) { throw "Schema Guard online report not found: $report" }
& $python -m eval_harness.evolution_analyzer_ab $report --candidate-variant schema_guard --output-dir outputs\evolution\real_schema_guard
if ($LASTEXITCODE -ne 0) { throw "Schema Guard promotion gate failed" }
Write-Host "Gate: outputs\evolution\real_schema_guard\latest_evolution_report.json"
