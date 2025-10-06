from __future__ import annotations
import os, sys, subprocess, threading, time, webbrowser, signal
from pathlib import Path

# Resolve app root whether frozen (PyInstaller) or source
if getattr(sys, "frozen", False):
    BASE = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    ROOT = Path(sys.executable).parent  # dist/AstroEngine
else:
    BASE = Path(__file__).resolve().parents[2]
    ROOT = BASE

# Default ports
API_PORT = int(os.environ.get("ASTROENGINE_API_PORT", "8000"))
UI_PORT = int(os.environ.get("ASTROENGINE_UI_PORT", "8501"))

# Ensure a writable workspace for user data
APPDATA = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / ".astroengine"))) / "AstroEngine"
APPDATA.mkdir(parents=True, exist_ok=True)

# Environment for child processes
env = os.environ.copy()
env.setdefault("ASTROENGINE_HOME", str(APPDATA))
env.setdefault("ASTROENGINE_API", f"http://127.0.0.1:{API_PORT}")
# Respect pre-set SE_EPHE_PATH if user configured; otherwise leave empty and Doctor will guide

# Resolve entry files
API_APP = "app.main:app"
STREAMLIT_ENTRY = BASE / "ui" / "streamlit" / "main_portal.py"
STREAMLIT_CONFIG_DIR = BASE / ".streamlit"

# When frozen, streamlit should read config.toml from a real dir
env.setdefault("STREAMLIT_SERVER_PORT", str(UI_PORT))
env.setdefault("STREAMLIT_SERVER_HEADLESS", "true")
env.setdefault("STREAMLIT_BROWSER_GATHERUSAGESTATS", "false")
env.setdefault("STREAMLIT_CONFIG_DIR", str(STREAMLIT_CONFIG_DIR))

api_proc: subprocess.Popen | None = None
ui_proc: subprocess.Popen | None = None


def start_api():
    global api_proc
    # Use uvicorn programmatically via module to avoid path issues
    cmd = [sys.executable, "-m", "uvicorn", API_APP, "--host", "127.0.0.1", "--port", str(API_PORT), "--log-level", "warning"]
    api_proc = subprocess.Popen(cmd, cwd=str(ROOT), env=env)


def start_ui():
    global ui_proc
    cmd = [sys.executable, "-m", "streamlit", "run", str(STREAMLIT_ENTRY), "--server.port", str(UI_PORT), "--server.headless", "true"]
    ui_proc = subprocess.Popen(cmd, cwd=str(ROOT), env=env)


def open_browser():
    time.sleep(1.5)
    try:
        webbrowser.open(f"http://127.0.0.1:{UI_PORT}")
    except Exception:
        pass


def main():
    start_api()
    # Wait a beat so UI can connect to API reliably
    time.sleep(0.8)
    start_ui()
    threading.Thread(target=open_browser, daemon=True).start()

    def shutdown(*_):
        if ui_proc and ui_proc.poll() is None:
            ui_proc.terminate()
        if api_proc and api_proc.poll() is None:
            api_proc.terminate()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Wait for UI to exit; if it dies early, also kill API
    code = 0
    try:
        code = ui_proc.wait() if ui_proc else 0
    finally:
        if api_proc and api_proc.poll() is None:
            api_proc.terminate()
        if api_proc:
            api_proc.wait(timeout=5)
    sys.exit(code)


if __name__ == "__main__":
    main()
