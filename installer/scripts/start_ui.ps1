$ErrorActionPreference = 'Stop'
$AppRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

# Use ProgramData for data/logs when installed under Program Files
$WritableRoot = if ($AppRoot -like "$($env:ProgramFiles)*") { Join-Path $env:ProgramData 'AstroEngine' } else { $AppRoot }
$LogDir  = Join-Path $WritableRoot 'logs'
$DataDir = Join-Path $WritableRoot 'var'
New-Item -ItemType Directory -Force -Path $LogDir,$DataDir | Out-Null

function Resolve-Python {
  $candidates = @(
    (Join-Path $AppRoot 'env\Scripts\python.exe'),
    (Join-Path $AppRoot 'venv\Scripts\python.exe'),
    (Join-Path $AppRoot 'runtime\python.exe')
  )
  foreach ($p in $candidates) { if (Test-Path $p) { return $p } }
  $cmd = Get-Command python.exe -ErrorAction SilentlyContinue
  if ($cmd) {
    $sys = $cmd.Source
    try { $ver = & $sys -c "import sys;print('{}.{}'.format(sys.version_info[0], sys.version_info[1]))"; if ($ver -eq '3.11') { return $sys } } catch {}
  }
  throw "Python 3.11/venv not found. Run Start AstroEngine (both) to auto-repair."
}
$py = Resolve-Python

# Point the app at the writable DB location and ensure imports resolve
$env:DATABASE_URL = "sqlite+pysqlite:///$($DataDir -replace '\\','/')/dev.db"
$env:PYTHONPATH   = $AppRoot

$log = Join-Path $LogDir 'start_ui.log'
Start-Transcript -Path $log -Append | Out-Null
try {
  & $py (Join-Path $AppRoot 'installer\windows_portal_entry.py') --launch ui --wait
  $code = $LASTEXITCODE
  Write-Host "Exit code: $code"
} finally {
  Stop-Transcript | Out-Null
  Read-Host "Press Enter to close"
}
exit $code
