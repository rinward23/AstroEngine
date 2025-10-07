# Build with:
#   pyinstaller packaging/windows/astroengine.spec --noconfirm
import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files
from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT
from PyInstaller.compat import is_win

root = os.path.abspath(".")
launcher = os.path.join(root, "packaging", "windows", "AstroEngineLauncher.py")

# Hidden imports: we run `-m streamlit` and `-m uvicorn` as subprocesses,
# so explicitly include their packages in the frozen app.
hidden = []
hidden += collect_submodules("streamlit")
hidden += collect_submodules("uvicorn")
hidden += collect_submodules("anyio")
hidden += collect_submodules("pkg_resources")  # quiets altgraph/pkg_resources warning
hidden += collect_submodules("pywebview")
hidden += collect_submodules("pystray")
hidden += collect_submodules("PIL")
hidden += collect_submodules("app.desktop")
hidden += collect_submodules("app")

# Data files from our own package
astro_data = collect_data_files(
    "astroengine",
    includes=[
        "**/*.yaml",
        "**/*.yml",
        "**/*.json",
        "**/*.csv",
        "**/*.toml",
        "**/*.html",
        "**/*.md",
        "**/*.txt",
    ],
    excludes=["**/__pycache__/**"],
)

desktop_data = collect_data_files(
    "app.desktop",
    includes=["**/*.yaml", "**/*.json"],
    excludes=["**/__pycache__/**"],
)

# Copy the UI source tree as plain files so Streamlit can run them by path
def tree(src, dst_prefix):
    # (src, dst) tuples for COLLECT
    res = []
    for dirpath, _, files in os.walk(src):
        for f in files:
            full = os.path.join(dirpath, f)
            rel = os.path.relpath(full, src)
            res.append((full, os.path.join(dst_prefix, rel)))
    return res

ui_tree = tree(os.path.join(root, "ui"), "ui")
streamlit_cfg = tree(os.path.join(root, ".streamlit"), ".streamlit") if os.path.isdir(".streamlit") else []

datas = astro_data + desktop_data + ui_tree + streamlit_cfg

a = Analysis(
    [launcher],
    pathex=[root],
    hiddenimports=hidden,
    datas=datas,
    binaries=[],
    noarchive=False,
)

pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name="AstroEngine",
    console=False,  # flip True if you want a debug console
    icon=os.path.join(root, "packaging", "windows", "icon.ico") if os.path.exists(os.path.join(root, "packaging", "windows", "icon.ico")) else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    name="AstroEngine",
)
