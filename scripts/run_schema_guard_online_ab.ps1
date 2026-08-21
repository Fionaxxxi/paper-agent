$ErrorActionPreference = "Stop"
$python = "D:\miniconda3\envs\paper_agent\python.exe"
if (-not (Test-Path $python)) { throw "PaperAgent Python environment not found: $python" }
& $python -m eval_harness.research_analyzer_schema_guard_ab --confirm-online
if ($LASTEXITCODE -ne 0) { throw "Schema Guard online A/B failed" }
Write-Host "Report: outputs\research_analyzer_prompt_ab\schema_guard\latest_analyzer_prompt_ab_online.json"
