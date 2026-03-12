param(
    [int]$Port = $(if ($env:PORT) { [int]$env:PORT } else { 8000 })
)

$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $PSScriptRoot
Set-Location $RootDir

$PythonExe = Join-Path $RootDir ".venv\Scripts\python.exe"

if (-not (Test-Path $PythonExe)) {
    Write-Host ".venv is missing. Run ./scripts/bootstrap.sh first."
    exit 1
}

$Listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
    Select-Object -Property OwningProcess -Unique

if ($Listeners) {
    Write-Host "Port $Port is already in use."
    Write-Host "Listening process:"

    foreach ($Listener in $Listeners) {
        $ProcessInfo = Get-CimInstance Win32_Process -Filter "ProcessId = $($Listener.OwningProcess)" -ErrorAction SilentlyContinue
        if ($ProcessInfo) {
            "{0,6} {1}" -f $ProcessInfo.ProcessId, $ProcessInfo.CommandLine
            continue
        }

        $Process = Get-Process -Id $Listener.OwningProcess -ErrorAction SilentlyContinue
        if ($Process) {
            "{0,6} {1}" -f $Process.Id, $Process.ProcessName
            continue
        }

        "{0,6}" -f $Listener.OwningProcess
    }

    Write-Host
    Write-Host "If this is an old dev server, stop it first:"
    Write-Host "  Stop-Process -Id <PID> -Force"
    Write-Host
    Write-Host "To run on a different port:"
    Write-Host "  `$env:PORT='8001'; .\scripts\dev.ps1"
    exit 1
}

Write-Host "Checking Playwright Chromium browsers..."
& $PythonExe -m app.config.playwright ensure
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

& $PythonExe -m uvicorn app.main:app --reload --port $Port
exit $LASTEXITCODE
