[CmdletBinding()]
param(
    [string]$PythonExe = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$testTempParent = Join-Path $repoRoot ".test-tmp"
$testTempRoot = Join-Path $testTempParent ("pytest-{0}-{1}" -f $PID, [guid]::NewGuid().ToString("N"))
if (-not $PythonExe) {
    $python312Venv = Join-Path $repoRoot ".venv-py312\Scripts\python.exe"
    $venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $python312Venv) {
        $PythonExe = $python312Venv
    }
    elseif (Test-Path -LiteralPath $venvPython) {
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
    $pythonVersion = & $PythonExe -c "import sys; print('.'.join(map(str, sys.version_info[:3])))"
    if ($LASTEXITCODE -ne 0) {
        throw "Could not query the Python interpreter version: $PythonExe"
    }
    $pythonVersion = $pythonVersion.Trim()
    if (-not $pythonVersion.StartsWith("3.12.")) {
        throw "Python 3.12 is required; found Python $pythonVersion at $PythonExe."
    }
    Write-Host "[verify] Python $pythonVersion"

    Invoke-CheckedPython -PythonArguments @("-m", "pip", "check")

    New-Item -ItemType Directory -Path $testTempParent -Force | Out-Null
    $baseTempArgument = "--basetemp=$testTempRoot"
    $collection = & $PythonExe -m pytest --collect-only -q -p no:cacheprovider -o addopts= $baseTempArgument 2>&1
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

    Invoke-CheckedPython -PythonArguments @("-m", "pytest", "-q", "-p", "no:cacheprovider", $baseTempArgument)
}
finally {
    Pop-Location
    if (Test-Path -LiteralPath $testTempRoot) {
        $resolvedParent = [System.IO.Path]::GetFullPath($testTempParent).TrimEnd('\') + '\'
        $resolvedTarget = [System.IO.Path]::GetFullPath($testTempRoot)
        if (-not $resolvedTarget.StartsWith($resolvedParent, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Refusing to clean pytest temp path outside $resolvedParent"
        }
        Remove-Item -LiteralPath $resolvedTarget -Recurse -Force
    }
}
