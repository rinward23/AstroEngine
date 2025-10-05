# Builds a windowed EXE that launches API + Streamlit UI
block_cipher = None

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

hiddenimports = []
hiddenimports += collect_submodules("pydantic")
hiddenimports += collect_submodules("sqlalchemy")
hiddenimports += collect_submodules("alembic")
hiddenimports += collect_submodules("uvicorn")
hiddenimports += collect_submodules("fastapi")
hiddenimports += collect_submodules("pyswisseph")


datas = []
datas += [("alembic.ini", "alembic.ini", "DATA")]
datas += [("migrations", "migrations")]
datas += [("ui/streamlit", "ui/streamlit")]


a = Analysis(
    [
        "app/desktop/launch_desktop.py",
    ],
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
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
    name="AstroEngine",
    console=False,
    icon=None,
)
