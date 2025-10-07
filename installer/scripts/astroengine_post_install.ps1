param(
  [Parameter(Mandatory=$true)] [string]$InstallRoot,
  [ValidateSet('Online','Offline')] [string]$Mode = 'Online',
  [ValidateSet('PerUser','AllUsers')] [string]$Scope = 'PerUser',
  [string]$ManifestPath,
  [string]$LogPath = "$env:TEMP\astroengine_post_install.log",
  [string]$PythonVersion = '3.11.13',
  [string]$PythonTargetRel = 'runtime',
  [string]$InstallPython = 'False'
)

$ErrorActionPreference = 'Stop'
if (-not $LogPath) {
  $LogPath = Join-Path $InstallRoot 'logs\install\post_install.log'
}
New-Item -ItemType Directory -Force -Path (Split-Path $LogPath -Parent) | Out-Null
Start-Transcript -Path $LogPath -Append | Out-Null

try {
  $installPythonFlag = $false
  try {
    if ($InstallPython -is [string]) {
      $installPythonFlag = [System.Convert]::ToBoolean($InstallPython)
    } else {
      $installPythonFlag = [bool]$InstallPython
    }
  } catch {
    $installPythonFlag = $false
  }

  $RuntimeDir = Join-Path $InstallRoot $PythonTargetRel
  $PyExe      = Join-Path $RuntimeDir 'python.exe'
  $VenvDir    = Join-Path $InstallRoot 'env'
  $DataDir    = Join-Path $InstallRoot 'var'
  New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null
  New-Item -ItemType Directory -Force -Path $DataDir | Out-Null

  function Ensure-Python {
    param([string]$Version, [string]$TargetDir, [string]$Mode, [string]$InstallRoot)
    if (Test-Path $PyExe) { return }
    $exeName = "python-$Version-amd64.exe"
    $offline = Join-Path $InstallRoot "installer\offline\$exeName"
    if ($Mode -eq 'Offline' -and (Test-Path $offline)) {
      $installer = $offline
    } else {
      $tmp = Join-Path $env:TEMP $exeName
      $url = "https://www.python.org/ftp/python/$Version/$exeName"
      Write-Host "Downloading Python: $url"
      Invoke-WebRequest -Uri $url -OutFile $tmp
      $installer = $tmp
    }
    $allUsers = if ($Scope -eq 'AllUsers') {'1'} else {'0'}
    $args = @('/quiet',"InstallAllUsers=$allUsers",'Include_pip=1','Include_test=0','SimpleInstall=1',"TargetDir=$TargetDir")
    Write-Host "Installing Python $Version to $TargetDir"
    $p = Start-Process -FilePath $installer -ArgumentList $args -Wait -PassThru
    if ($p.ExitCode -ne 0) { throw "Python installer failed with code $($p.ExitCode)" }
  }

  if ($installPythonFlag -or -not (Test-Path $PyExe)) {
    Ensure-Python -Version $PythonVersion -TargetDir $RuntimeDir -Mode $Mode -InstallRoot $InstallRoot
  }

  if (-not (Test-Path $VenvDir)) {
    Write-Host "Creating virtual environment at $VenvDir"
    & $PyExe -m venv $VenvDir
  }

  $venvPy = Join-Path $VenvDir 'Scripts\python.exe'
  & $venvPy -m pip install --upgrade pip wheel

  $req = Join-Path $InstallRoot 'requirements.txt'
  if ($Mode -eq 'Offline') {
    $wheels = Join-Path $InstallRoot 'installer\offline\wheels'
    & $venvPy -m pip install --no-index --find-links $wheels -r $req
  } else {
    & $venvPy -m pip install -r $req
  }

  $env:DATABASE_URL = "sqlite+pysqlite:///$($DataDir -replace '\\','/')/dev.db"
  Push-Location $InstallRoot
  try {
    & (Join-Path $VenvDir 'Scripts\alembic.exe') upgrade head
  } finally {
    Pop-Location
  }

  Write-Host 'Post-install complete.'
}
finally {
  Stop-Transcript | Out-Null
}
