# installer\scripts\start_ui.ps1
$ErrorActionPreference = 'Stop'
$AppRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$LogDir  = Join-Path $AppRoot 'logs'
$RunDir  = Join-Path $AppRoot 'run'
New-Item -ItemType Directory -Force -Path $LogDir,$RunDir | Out-Null

function Resolve-Python {
  $candidates = @(
    (Join-Path $AppRoot 'env\Scripts\python.exe'),
    (Join-Path $AppRoot 'venv\Scripts\python.exe'),
    (Join-Path $AppRoot 'runtime\python.exe')
  )
  foreach ($p in $candidates) {
    if (Test-Path $p) { return $p }
  }

  # Try system Python 3.11 from PATH
  $sys = (Get-Command python.exe -ErrorAction SilentlyContinue)?.Source
  if ($sys) {
    $ver = & $sys -c "import sys;print('.'.join(map(str,sys.version_info[:2])))"
    if ($ver -eq '3.11') { return $sys }
  }

  Write-Host "No suitable Python found. Attempting repair..."
  & "$PSScriptRoot\astroengine_post_install.ps1" -InstallRoot $AppRoot -Mode Online -Scope PerUser -InstallPython `
      -ManifestPath (Join-Path $AppRoot 'installer\manifests\online_python.json') `
      -LogPath (Join-Path $LogDir 'post_install-autofix.log')
  $after = Join-Path $AppRoot 'env\Scripts\python.exe'
  if (Test-Path $after) { return $after }
  throw "Python 3.11/venv still missing. See logs in $LogDir"
}

$py = Resolve-Python

$env:DATABASE_URL = "sqlite+pysqlite:///$($AppRoot -replace '\\','/')/var/dev.db"

# rotate log (keep 5)
$log = Join-Path $LogDir 'start_ui.log'
if (Test-Path $log) {
  for ($i=4; $i -ge 1; $i--) {
    $src = "$log.$i"
    $dst = "$log." + ($i + 1)
    if (Test-Path $src) { Move-Item $src $dst -Force }
  }
  Move-Item $log "$log.1" -Force
}

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
