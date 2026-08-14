$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = "D:\miniconda3\envs\paper_agent\python.exe"

if (-not (Test-Path -LiteralPath $Python)) {
    throw "未找到项目虚拟环境 Python：$Python"
}

Push-Location $ProjectRoot
try {
    & $Python -m eval_harness.prompt_security_eval @args
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
