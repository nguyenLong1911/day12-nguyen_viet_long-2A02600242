param(
    [int]$StartupTimeoutSec = 180,
    [int]$PollIntervalSec = 3,
    [string]$BaseUrl = "http://localhost:8080"
)

$ErrorActionPreference = "Stop"

function Wait-Http200 {
    param(
        [string]$Url,
        [int]$TimeoutSec,
        [int]$IntervalSec
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        try {
            $resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
            if ($resp.StatusCode -eq 200) {
                return $true
            }
        } catch {
            # Ignore transient startup errors and keep polling.
        }
        Start-Sleep -Seconds $IntervalSec
    }

    return $false
}

Set-Location $PSScriptRoot

Write-Host "[1/5] Stop old stack..."
docker compose down -v | Out-Host

Write-Host "[2/5] Start stack with 3 agents..."
docker compose up -d --build --scale agent=3 | Out-Host

Write-Host "[3/5] Wait for /health and /ready = 200..."
$healthOk = Wait-Http200 -Url "$BaseUrl/health" -TimeoutSec $StartupTimeoutSec -IntervalSec $PollIntervalSec
$readyOk = Wait-Http200 -Url "$BaseUrl/ready" -TimeoutSec $StartupTimeoutSec -IntervalSec $PollIntervalSec

if (-not ($healthOk -and $readyOk)) {
    Write-Host "Readiness timeout. Current status:"
    docker compose ps | Out-Host
    docker compose logs --tail=100 | Out-Host
    throw "Service was not ready within timeout."
}

Write-Host "[4/5] Smoke test /ask 3 requests..."
1..3 | ForEach-Object {
    $response = Invoke-RestMethod -Method Post -Uri "$BaseUrl/ask" -ContentType "application/json" -Headers @{"X-API-Key"="secret-key-123"} -Body '{"user_id":"u1","question":"hello"}'
    Write-Host "served_by=$($response.served_by)"
}

Write-Host "[5/5] Run stateless test..."
python test_stateless.py | Out-Host

Write-Host "Done."