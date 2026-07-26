param([switch]$Headless, [switch]$BackendOnly, [switch]$NoBrowser)
$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $PSCommandPath
$BackendPort = 11131
$FrontendPort = 11130

Write-Host "=== pdf-mcp startup ===" -ForegroundColor Cyan

# Kill zombies
Get-NetTCPConnection -LocalPort $BackendPort -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
Get-NetTCPConnection -LocalPort $FrontendPort -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }

# Ensure data dirs
New-Item -ItemType Directory -Force -Path "$ScriptRoot\data\uploads", "$ScriptRoot\data\lancedb" | Out-Null

# Start backend
$env:MCP_MODE = "http"
$env:MCP_PORT = "$BackendPort"
$env:MCP_HOST = "127.0.0.1"

$BackendJob = Start-Job -Name "pdf-mcp-backend" -ScriptBlock {
    param($Root, $Port)
    Set-Location $Root
    uv run python run_server.py --mode http --host 127.0.0.1 --port $Port
} -ArgumentList $ScriptRoot, $BackendPort

# Poll for readiness
Write-Host "Waiting for backend..." -ForegroundColor Yellow
for ($i = 0; $i -lt 60; $i++) {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:$BackendPort/api/health" -TimeoutSec 2 -UseBasicParsing -ErrorAction SilentlyContinue
        if ($r.StatusCode -eq 200) { Write-Host "Backend ready on port $BackendPort" -ForegroundColor Green; break }
    } catch {}
    Start-Sleep 1
}

if ($BackendOnly) {
    Write-Host "Backend only mode. Press Ctrl+C to stop." -ForegroundColor Cyan
    while ($true) { Start-Sleep 10 }
}

# Start frontend
$WebRoot = Join-Path $ScriptRoot "webapp"
Write-Host "Starting frontend..." -ForegroundColor Yellow
$FrontendProcess = Start-Process -NoNewWindow -PassThru -FilePath "bun" -ArgumentList "run dev" -WorkingDirectory $WebRoot

Start-Sleep 3

if (-not $NoBrowser) {
    Start-Process "http://127.0.0.1:$FrontendPort"
}

Write-Host "=== pdf-mcp running ===" -ForegroundColor Green
Write-Host "  Backend:  http://127.0.0.1:$BackendPort" -ForegroundColor Cyan
Write-Host "  Frontend: http://127.0.0.1:$FrontendPort" -ForegroundColor Cyan
Write-Host "  Health:   http://127.0.0.1:$BackendPort/api/health" -ForegroundColor Cyan
Write-Host "  MCP SSE:  http://127.0.0.1:$BackendPort/mcp" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow

try {
    while ($true) {
        if ($BackendJob.State -eq "Completed" -or $BackendJob.State -eq "Failed") {
            Receive-Job $BackendJob
            break
        }
        Start-Sleep 2
    }
} finally {
    if (-not $BackendOnly) { Stop-Process -Id $FrontendProcess.Id -Force -ErrorAction SilentlyContinue }
    Stop-Job $BackendJob -ErrorAction SilentlyContinue
    Remove-Job $BackendJob -ErrorAction SilentlyContinue
}
