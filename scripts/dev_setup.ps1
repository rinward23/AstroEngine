# >>> AUTO-GEN BEGIN: AE Dev Setup (PowerShell) v1.1
param([switch]$Conda)
if ($Conda) {
  conda env update -f environment.yml --prune
  Write-Host "Activate with: conda activate astroengine"
} else {
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  python -m pip install --upgrade pip
  pip install -e .[dev]
}
python -m astroengine env
# >>> AUTO-GEN END: AE Dev Setup (PowerShell) v1.1
