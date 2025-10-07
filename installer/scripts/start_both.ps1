# PS 5.1-compatible launcher
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
  foreach ($p in $candidates) { if (Test-Path $p) { return $p } }

  $cmd = Get-Command python.exe -ErrorAction SilentlyContinue
  if ($cmd) {
    $sys = $cmd.Source
    try {
      $ver = & $sys -c "import sys;print('{}.{}'.format(sys.version_info[0], sys.version_info[1]))"
      if ($ver -eq '3.11') { return $sys }
    } catch {}
  }

  Write-Host "No suitable Python found. Attempting repair..."
  $scope = ( ($AppRoot -like "$($env:ProgramFiles)*") ? 'AllUsers' : 'PerUser' )
  & (Join-Path $PSScriptRoot 'astroengine_post_install.ps1') `
      -InstallRoot $AppRoot -Mode Online -Scope $scope -InstallPython `
      -ManifestPath (Join-Path $AppRoot 'installer\manifests\online_python.json') `
      -LogPath (Join-Path $LogDir 'post_install-autofix.log')
  $after = Join-Path $AppRoot 'env\Scripts\python.exe'
  if (Test-Path $after) { return $after }
  throw "Python 3.11/venv still missing. See logs in $LogDir"
}

$py = Resolve-Python
$env:DATABASE_URL = "sqlite+pysqlite:///$($AppRoot -replace '\\','/')/var/dev.db"

# rotate logs (keep 5)
$log = Join-Path $LogDir 'start_both.log'
if (Test-Path $log) {
  for ($i=4; $i -ge 1; $i--) {
    $src = "$log.$i"; $dst = "$log." + ($i+1)
    if (Test-Path $src) { Move-Item $src $dst -Force }
  }
  Move-Item $log "$log.1" -Force
}

Start-Transcript -Path $log -Append | Out-Null
try {
  & $py (Join-Path $AppRoot 'installer\windows_portal_entry.py') --launch both --wait
  $code = $LASTEXITCODE
  Write-Host "Exit code: $code"
} finally {
  Stop-Transcript | Out-Null
  Read-Host "Press Enter to close"
}
exit $code
