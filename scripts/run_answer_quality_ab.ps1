param(
    [switch]$ConfirmOnline,
    [string]$InputReport = "",
    [string]$RerunPaperAgentCase = "",
    [string]$MergeReport = "outputs/answer_quality_ab/latest_answer_quality_ab.json"
)

$ErrorActionPreference = "Stop"
$python = "D:\miniconda3\envs\paper_agent\python.exe"
$arguments = @("-m", "eval_harness.answer_quality_ab")

if ($RerunPaperAgentCase) {
    if (-not $ConfirmOnline) { throw "Targeted rerun requires -ConfirmOnline" }
    $arguments += @("--confirm-online", "--rerun-paper-agent-case", $RerunPaperAgentCase, "--merge-report", $MergeReport)
} elseif ($InputReport) {
    $arguments += @("--input-report", $InputReport)
} elseif ($ConfirmOnline) {
    $arguments += "--confirm-online"
} else {
    throw "This evaluation calls the real model. Re-run with -ConfirmOnline, or provide -InputReport for zero-LLM regrading."
}

& $python @arguments
if ($LASTEXITCODE -ne 0) { throw "Answer quality A/B evaluation failed" }
