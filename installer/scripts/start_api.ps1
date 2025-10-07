$ErrorActionPreference = 'Continue'
$AppRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$LogDir  = Join-Path $AppRoot 'logs'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$env:DATABASE_URL = "sqlite+pysqlite:///$($AppRoot -replace '\\','/')/var/dev.db"
Start-Transcript -Path (Join-Path $LogDir 'start_api.log') -Append | Out-Null
& (Join-Path $AppRoot 'env\Scripts\python.exe') (Join-Path $AppRoot 'installer\windows_portal_entry.py') --launch api --wait --no-browser
$code = $LASTEXITCODE
Write-Host "Exit code: $code"
Stop-Transcript | Out-Null
Read-Host "Press Enter to close"
exit $code
