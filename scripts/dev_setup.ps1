# >>> AUTO-GEN BEGIN: AstroEngine Dev Setup (PowerShell) v1.0
param([switch]$Conda)

if ($Conda) {
  conda env update -f environment.yml --prune
  Write-Host "[setup] Activate with: conda activate astroengine"
} else {
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  python -m pip install --upgrade pip
  if (Test-Path pyproject.toml) {
    pip install -e .[dev,api,charts,locational,fallback-ephemeris]
  } else {
    pip install -r requirements.txt
  }
}
python scripts/swe_smoketest.py
# >>> AUTO-GEN END: AstroEngine Dev Setup (PowerShell) v1.0
