param(
  [Parameter(Mandatory=$true)] [string]$InstallRoot,
  [ValidateSet('Online','Offline')] [string]$Mode = 'Online',
  [ValidateSet('PerUser','AllUsers')] [string]$Scope = 'PerUser',
  [string]$ManifestPath,
  [string]$LogPath = "$env:TEMP\astroengine_post_install.log",
  [string]$PythonVersion = '3.11.13',
  [string]$PythonTargetRel = 'runtime',
  [switch]$InstallPython
)

$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Force -Path (Split-Path $LogPath -Parent) | Out-Null
Start-Transcript -Path $LogPath -Append | Out-Null

$RuntimeDir = Join-Path $InstallRoot 'runtime'
$PyExe      = Join-Path $RuntimeDir 'python.exe'
$VenvDir    = Join-Path $InstallRoot 'env'

# Choose writable root for data/logs (ProgramData for all-users)
$WritableRoot = if ($InstallRoot -like "$($env:ProgramFiles)*") { Join-Path $env:ProgramData 'AstroEngine' } else { $InstallRoot }
$DataDir = Join-Path $WritableRoot 'var'
$LogDir  = Join-Path $WritableRoot 'logs'
New-Item -ItemType Directory -Force -Path $DataDir,$LogDir | Out-Null

function Ensure-Python {
  param([string]$Version,[string]$TargetDir,[string]$Mode,[string]$InstallRoot)
  if (Test-Path $PyExe) { return }
  $exe = "python-$Version-amd64.exe"
  $offline = Join-Path $InstallRoot "installer\offline\$exe"
  if ($Mode -eq 'Offline' -and (Test-Path $offline)) {
    $installer = $offline
  } else {
    $tmp = Join-Path $env:TEMP $exe
    Invoke-WebRequest "https://www.python.org/ftp/python/$Version/$exe" -OutFile $tmp
    $installer = $tmp
  }
  $all = if ($Scope -eq 'AllUsers') {'1'} else {'0'}
  $args = @('/quiet',"InstallAllUsers=$all",'Include_pip=1','Include_test=0','SimpleInstall=1',"TargetDir=$TargetDir")
  $p = Start-Process -FilePath $installer -ArgumentList $args -Wait -PassThru
  if ($p.ExitCode -ne 0) { throw "Python installer failed: $($p.ExitCode)" }
}

if ($InstallPython -or -not (Test-Path $PyExe)) {
  Ensure-Python -Version $PythonVersion -TargetDir $RuntimeDir -Mode $Mode -InstallRoot $InstallRoot
}

if (-not (Test-Path $VenvDir)) { & $PyExe -m venv $VenvDir }
$venvPy = Join-Path $VenvDir 'Scripts\python.exe'
& $venvPy -m pip install --upgrade pip wheel

$req = Join-Path $InstallRoot 'requirements\base.txt'
if ($Mode -eq 'Offline') {
  $wheels = Join-Path $InstallRoot 'installer\offline\wheels'
  & $venvPy -m pip install --no-index --find-links $wheels -r $req
} else {
  & $venvPy -m pip install -r $req
}

$env:PYTHONPATH = $InstallRoot
$env:DATABASE_URL = "sqlite+pysqlite:///$($DataDir -replace '\\','/')/dev.db"
Push-Location $InstallRoot
try {
  & (Join-Path $VenvDir 'Scripts\alembic.exe') upgrade head
} finally { Pop-Location }

Stop-Transcript | Out-Null
Write-Host "Post-install complete."
