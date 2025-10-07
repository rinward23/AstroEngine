# Build the AstroEngine Streamlit portal with bundled ephemeris data.

block_cipher = None

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

hiddenimports = []
hiddenimports += collect_submodules("pydantic")
hiddenimports += collect_submodules("sqlalchemy")
hiddenimports += collect_submodules("streamlit")
hiddenimports += collect_submodules("uvicorn")
hiddenimports += collect_submodules("fastapi")
hiddenimports += collect_submodules("pyswisseph")


datas = []
datas += collect_data_files("astroengine", includes=["py.typed"])
datas += [("ui/streamlit", "ui/streamlit")]
datas += [("datasets/swisseph_stub", "resources/ephemeris")]


a = Analysis(
    [
        "installer/windows_portal_entry.py",
    ],
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=["packaging/hooks"],
    runtime_hooks=["packaging/hooks/rthook-astroengine-portal.py"],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name="AstroEnginePortal",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    icon=None,
)
