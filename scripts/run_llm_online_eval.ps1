$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = "D:\miniconda3\envs\paper_agent\python.exe"
$OutputDir = Join-Path $ProjectRoot "outputs\llm_core_eval"
for ($Index = 0; $Index -lt $args.Count; $Index++) {
    if (($args[$Index] -eq "--output-dir") -and ($Index + 1 -lt $args.Count)) {
        $RequestedOutput = $args[$Index + 1]
        $OutputDir = if ([System.IO.Path]::IsPathRooted($RequestedOutput)) {
            $RequestedOutput
        } else {
            Join-Path $ProjectRoot $RequestedOutput
        }
        break
    }
}
$Json = Join-Path $OutputDir "latest_llm_online.json"
$Excel = Join-Path $OutputDir "latest_llm_online.xlsx"
$Preview = Join-Path $OutputDir "previews"

if (-not (Test-Path -LiteralPath $Python)) {
    throw "未找到项目虚拟环境 Python：$Python"
}

Push-Location $ProjectRoot
try {
    & $Python -m eval_harness.llm_online_eval --confirm-online @args
    $EvalExit = $LASTEXITCODE
    if (Test-Path -LiteralPath $Json) {
        node scripts\build_llm_online_report.mjs $Json $Excel $Preview
        # artifact-tool occasionally returns a native non-zero exit code on Windows
        # after the workbook has already been exported. The artifact itself is the
        # reliable completion signal; missing/empty output is still a hard failure.
        if ((-not (Test-Path -LiteralPath $Excel)) -or ((Get-Item -LiteralPath $Excel).Length -eq 0)) {
            throw "Excel report generation failed"
        }
    }
    Write-Host "`nOnline evaluation finished"
    Write-Host "JSON : $Json"
    Write-Host "CSV  : $(Join-Path $OutputDir 'latest_llm_online.csv')"
    Write-Host "Excel: $Excel"
    exit $EvalExit
}
finally {
    Pop-Location
}
