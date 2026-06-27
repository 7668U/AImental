$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Backend = Join-Path $Root "AImental_backend"
$Python = Join-Path $Backend ".venv\Scripts\python.exe"
$Logs = Join-Path $Root "logs"
$WorkerPidFile = Join-Path $Logs "worker.pid"

New-Item -ItemType Directory -Force -Path $Logs | Out-Null

function Start-ManagedProcess {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string[]]$ArgumentList,
        [Parameter(Mandatory = $true)][string]$WorkingDirectory,
        [Parameter(Mandatory = $true)][string]$StdOut,
        [Parameter(Mandatory = $true)][string]$StdErr
    )

    $quotedArgs = ($ArgumentList | ForEach-Object { '"' + ($_ -replace '"', '\"') + '"' }) -join " "
    $command = 'cd /d "' + $WorkingDirectory + '" && "' + $FilePath + '" ' + $quotedArgs + ' 1> "' + $StdOut + '" 2> "' + $StdErr + '"'
    cmd.exe /c start "" /B cmd.exe /c $command
}

if (-not (Test-Path $Python)) {
    Write-Host "Backend .venv not found. Creating it with Python 3.12..."
    py -3.12 -m venv (Join-Path $Backend ".venv")
    & $Python -m pip install --upgrade pip
    & $Python -m pip install -r (Join-Path $Backend "requirements.txt")
}

$redis = Get-Command redis-server -ErrorAction SilentlyContinue
if ($redis -and -not (Get-NetTCPConnection -LocalPort 6379 -State Listen -ErrorAction SilentlyContinue)) {
    Write-Host "Starting Redis..."
    cmd.exe /c start "" /B $redis.Source --bind 127.0.0.1 --port 6379
    Start-Sleep -Seconds 2
}

if (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue) {
    Write-Host "Port 8000 is already in use. Skipping uvicorn startup."
} else {
    Write-Host "Starting FastAPI backend..."
    Start-ManagedProcess `
        -FilePath $Python `
        -ArgumentList @("-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info") `
        -WorkingDirectory $Backend `
        -StdOut (Join-Path $Logs "backend.out.log") `
        -StdErr (Join-Path $Logs "backend.err.log") | Out-Null
}

$workerRunning = $false
if (Test-Path $WorkerPidFile) {
    $workerRunning = $true
}

if (-not $workerRunning) {
    Write-Host "Starting background worker..."
    $worker = Start-ManagedProcess `
        -FilePath $Python `
        -ArgumentList @("background_worker.py") `
        -WorkingDirectory $Backend `
        -StdOut (Join-Path $Logs "worker.out.log") `
        -StdErr (Join-Path $Logs "worker.err.log")
    "started" | Set-Content -Path $WorkerPidFile
} else {
    Write-Host "Background worker is already running. Skipping worker startup."
}

Start-Sleep -Seconds 2
Write-Host ""
Write-Host "Current port status:"
Get-NetTCPConnection -LocalPort 6379,8000 -ErrorAction SilentlyContinue |
    Select-Object LocalAddress, LocalPort, State, OwningProcess |
    Format-Table

Write-Host "Backend URL: http://127.0.0.1:8000"
Write-Host "API docs: http://127.0.0.1:8000/docs"
