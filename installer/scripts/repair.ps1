$ErrorActionPreference = 'Stop'
$AppRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$LogDir = Join-Path $AppRoot 'logs\install'
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$mode  = 'Online'
$scope = ( ($AppRoot -like "$($env:ProgramFiles)*") ? 'AllUsers' : 'PerUser' )
& (Join-Path $PSScriptRoot 'astroengine_post_install.ps1') `
  -InstallRoot $AppRoot -Mode $mode -Scope $scope -InstallPython `
  -ManifestPath (Join-Path $AppRoot 'installer\manifests\online_python.json') `
  -LogPath (Join-Path $LogDir 'post_install-repair.log')
Read-Host "Repair complete. Press Enter to close."
