# >>> AUTO-GEN BEGIN: Docs Setup v1.0
## Local Setup
```bash
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -U pip
pip install -r requirements.txt -r dev-requirements.txt
# Optional features:
pip install -r requirements-optional.txt

# Swiss Ephemeris data (Ubuntu/Debian):
sudo apt-get update && sudo apt-get install -y swe-data
export SE_EPHE_PATH=/usr/share/sweph
# Windows (PowerShell): $env:SE_EPHE_PATH="C:/AstroEngine/ephe"
# Windows (Command Prompt, persistent): setx SE_EPHE_PATH "C:\AstroEngine\ephe"

Dev Hygiene

pre-commit install
ruff check .
pytest -q
```

>>> AUTO-GEN END: Docs Setup v1.0
