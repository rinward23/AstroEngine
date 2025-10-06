# Build with: pyinstaller packaging/windows/astroengine.spec
import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

project_root = os.path.abspath(".")

ui_data = collect_data_files(
    "ui",
    includes=[
        "streamlit/**/*.py",
        "streamlit/**/*.json",
        "streamlit/**/*.yaml",
        "streamlit/**/*.toml",
        "streamlit/**/*.txt",
    ],
    excludes=["**/__pycache__/**"],
)
astro_data = collect_data_files(
    "astroengine",
    includes=["**/*.yaml", "**/*.yml", "**/*.json", "**/*.csv", "**/*.toml"],
    excludes=["**/__pycache__/**"],
)

datas = []
datas += ui_data
datas += astro_data
datas += [(".streamlit", ".streamlit")]

hiddenimports = []
for pkg in ("pkg_resources", "streamlit", "uvicorn", "anyio"):
    hiddenimports += collect_submodules(pkg)


a = Analysis(
    ["packaging/windows/AstroEngineLauncher.py"],
    pathex=[project_root],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=["packaging/hooks"],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name="AstroEngine",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="packaging/windows/icon.ico" if os.path.exists("packaging/windows/icon.ico") else None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="AstroEngine",
)
