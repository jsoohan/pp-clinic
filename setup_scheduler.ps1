# ─────────────────────────────────────────────────────────────
# Windows 작업 스케줄러 자동 등록 스크립트
# 실행: powershell -ExecutionPolicy Bypass -File setup_scheduler.ps1
# ─────────────────────────────────────────────────────────────

$scriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonExe  = (Get-Command python).Source
$taskScript = Join-Path $scriptDir "run.py"
$logFile    = Join-Path $scriptDir "logs\dashboard_daily.log"

# 로그 폴더 생성
New-Item -ItemType Directory -Force -Path (Join-Path $scriptDir "logs") | Out-Null

# ─── 작업 설정 ───
$action  = New-ScheduledTaskAction `
    -Execute $pythonExe `
    -Argument "`"$taskScript`" dashboard" `
    -WorkingDirectory $scriptDir

$trigger = New-ScheduledTaskTrigger `
    -Daily `
    -At "07:00AM"   # 매일 오전 7시 데이터 갱신

$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 1) `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable

# ─── 등록 ───
$taskName = "PPClinic_Dashboard_Daily"

# 기존 작업 제거 (있는 경우)
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

Register-ScheduledTask `
    -TaskName $taskName `
    -Action   $action `
    -Trigger  $trigger `
    -Settings $settings `
    -Description "팽팽클리닉 대시보드 데이터 자동 갱신 (매일 07:00)" `
    -RunLevel Highest

Write-Host ""
Write-Host "✅ 스케줄러 등록 완료: $taskName" -ForegroundColor Green
Write-Host "   • 실행 시각: 매일 오전 07:00"
Write-Host "   • Python: $pythonExe"
Write-Host "   • 스크립트: $taskScript dashboard"
Write-Host ""
Write-Host "▶ 지금 당장 실행하려면:" -ForegroundColor Cyan
Write-Host "   python run.py dashboard"
Write-Host ""
Write-Host "▶ 스케줄러 상태 확인:" -ForegroundColor Cyan
Write-Host "   Get-ScheduledTask -TaskName '$taskName' | Get-ScheduledTaskInfo"
