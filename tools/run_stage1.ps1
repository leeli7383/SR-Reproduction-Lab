param(
    [string]$Python = 'D:/CodexTools/sr-reproduction/venv/Scripts/python.exe'
)
$ErrorActionPreference = 'Stop'
$srRoot = Split-Path -Parent $PSScriptRoot
Push-Location $srRoot
try {
    if (-not (Test-Path -LiteralPath $Python)) { throw 'See docs/ENVIRONMENT.md to prepare the isolated Python environment.' }
    $srRunId = Get-Date -Format 'yyyyMMdd-HHmmss'
    $srOutput = "artifacts/runs/$srRunId"
    New-Item -ItemType Directory -Path 'logs' -Force | Out-Null
    & $Python tools/bootstrap_runtime.py *> "logs/$srRunId-bootstrap.log"
    if ($LASTEXITCODE -ne 0) { throw "Bootstrap failed: logs/$srRunId-bootstrap.log" }
    & $Python tools/prepare_benchmarks.py *> "logs/$srRunId-data.log"
    if ($LASTEXITCODE -ne 0) { throw "Data preparation failed: logs/$srRunId-data.log" }
    & $Python -m unittest discover -s tests -v *> "logs/$srRunId-tests.log"
    if ($LASTEXITCODE -ne 0) { throw "Tests failed: logs/$srRunId-tests.log" }
    & $Python -m sr_lab.evaluate --output $srOutput *> "logs/$srRunId-evaluation.log"
    if ($LASTEXITCODE -ne 0) { throw "Evaluation failed: logs/$srRunId-evaluation.log" }
    & $Python tools/verify_reference_metrics.py --run $srOutput *> "logs/$srRunId-reference-check.log"
    if ($LASTEXITCODE -ne 0) { throw "Reference metric check failed: logs/$srRunId-reference-check.log" }
    & $Python -m sr_lab.train_smoke *> "logs/$srRunId-training-smoke.log"
    if ($LASTEXITCODE -ne 0) { throw "Training smoke failed: logs/$srRunId-training-smoke.log" }
    @{run_id=$srRunId; output=$srOutput; status='passed'; api_calls='not invoked by this runner'} |
        ConvertTo-Json | Set-Content -LiteralPath 'artifacts/latest_stage1.json' -Encoding utf8
    Write-Output "Stage 1 passed. Results: $srOutput/summary.json"
} finally {
    Pop-Location
}
