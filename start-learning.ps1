param(
    [ValidateSet('local', 'public')][string]$Source = 'local',
    [ValidateRange(1024, 65535)][int]$Port = 8765
)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONUTF8 = '1'
$runtimeCandidates = @()
$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if ($pythonCommand -and $pythonCommand.Source -notlike '*WindowsApps*') {
    $runtimeCandidates += $pythonCommand.Source
}
$quarkRuntimeRoot = Join-Path $env:LOCALAPPDATA 'Quark\User Data\quark-agent\resources\runtimes\python'
if (Test-Path -LiteralPath $quarkRuntimeRoot) {
    $runtimeCandidates += Get-ChildItem -LiteralPath $quarkRuntimeRoot -Filter python.exe -Recurse | Sort-Object FullName -Descending | Select-Object -ExpandProperty FullName
}
$learningPython = $null
foreach ($candidate in $runtimeCandidates) {
    & $candidate -c 'import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)'
    if ($LASTEXITCODE -eq 0) { $learningPython = $candidate; break }
}
if (-not $learningPython) { throw 'Please install Python 3.11+ and make python available on PATH.' }
if (-not (Get-Command node -ErrorAction SilentlyContinue)) { throw 'Please install Node.js 20+ for local preview.' }
& $learningPython build_learning.py --source $Source
if ($LASTEXITCODE -ne 0) { throw 'Learning app build failed.' }
$env:PORT = [string]$Port
Write-Host "Open http://127.0.0.1:$Port . Press Ctrl+C to stop."
& node serve.mjs
