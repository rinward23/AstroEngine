param(
  [switch]$WithObs
)
$ErrorActionPreference = "Stop"

# 1) Fresh venv with Python 3.11
python -V
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
python -m pip install -U pip wheel setuptools

# 2) Install project + extras (API, providers, UI)
$extras = "api,providers,ui"
if ($WithObs) { $extras = "$extras,obs" }
pip install -e ".[${extras}]"

# 3) PyInstaller
# Pin to the vetted 6.10 series so the build finds the CLI entry points.
pip install 'pyinstaller==6.10.*'

# 4) Build EXEs
pyinstaller packaging/astroengine_cli.spec --noconfirm
pyinstaller packaging/astroengine_gui.spec --noconfirm
pyinstaller packaging/astroengine_portal.spec --noconfirm

Write-Host "Build complete. Artifacts in .\\dist\\"
