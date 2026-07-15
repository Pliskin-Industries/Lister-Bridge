[CmdletBinding()]
param(
    [string]$PythonExe = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
if (-not $PythonExe) {
    $venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $venvPython) {
        $PythonExe = $venvPython
    }
    else {
        $PythonExe = (Get-Command python -ErrorAction Stop).Source
    }
}

function Invoke-CheckedPython {
    param([string[]]$PythonArguments)

    & $PythonExe @PythonArguments
    if ($LASTEXITCODE -ne 0) {
        throw "Python command failed with exit code ${LASTEXITCODE}: $PythonExe $($PythonArguments -join ' ')"
    }
}

Push-Location $repoRoot
try {
    Write-Host "[verify] interpreter: $PythonExe"
    Invoke-CheckedPython -PythonArguments @("--version")
    Invoke-CheckedPython -PythonArguments @("-m", "pip", "check")

    $collection = & $PythonExe -m pytest --collect-only -q -p no:cacheprovider -o addopts= 2>&1
    $collectionExit = $LASTEXITCODE
    $collectionText = ($collection | Out-String)
    Write-Host $collectionText.TrimEnd()
    if ($collectionExit -ne 0) {
        throw "Pytest collection failed with exit code $collectionExit"
    }

    $match = [regex]::Match($collectionText, "(?m)(\d+)\s+tests?\s+collected")
    if (-not $match.Success) {
        throw "Could not parse the pytest collection count."
    }
    $testCount = [int]$match.Groups[1].Value
    if ($testCount -lt 166) {
        throw "Collected $testCount tests; the protected baseline is 166."
    }
    Write-Host "[verify] collected tests: $testCount"

    Invoke-CheckedPython -PythonArguments @("-m", "pytest", "-q", "-p", "no:cacheprovider")
}
finally {
    Pop-Location
}
