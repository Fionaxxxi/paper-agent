$ErrorActionPreference = "Stop"

$python = "D:\miniconda3\envs\paper_agent\python.exe"
if (-not (Test-Path $python)) {
    throw "PaperAgent Python environment not found: $python"
}

& $python -m eval_harness.evolution_cycle
if ($LASTEXITCODE -ne 0) {
    throw "Controlled evolution cycle failed"
}

Write-Host "Report: outputs\evolution\latest_evolution_report.json"
Write-Host "Failures: outputs\evolution\latest_evolution_failures.csv"
Write-Host "Candidates: outputs\evolution\latest_evolution_candidates.csv"
Write-Host "Registry: outputs\evolution\strategy_versions.json"
