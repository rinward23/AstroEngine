from __future__ import annotations
import os, sys, subprocess, threading, time, signal, socket
from pathlib import Path

try:
    import urllib.request, urllib.error
except Exception:
    urllib = None  # type: ignore

# -------- Paths --------
if getattr(sys, "frozen", False):
    BASE = Path(sys.executable).parent   # dist/AstroEngine
    ROOT = BASE
else:
    BASE = Path(__file__).resolve().parents[2]
    ROOT = BASE

API_PORT = int(os.environ.get("ASTROENGINE_API_PORT", "8000"))
UI_PORT = int(os.environ.get("ASTROENGINE_UI_PORT", "8501"))
AUTO_OPEN = os.environ.get("ASTROENGINE_NO_BROWSER", "0") not in ("1", "true", "TRUE")
APPDATA = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / ".astroengine"))) / "AstroEngine"
APPDATA.mkdir(parents=True, exist_ok=True)

env = os.environ.copy()
env.setdefault("ASTROENGINE_HOME", str(APPDATA))
env.setdefault("ASTROENGINE_API", f"http://127.0.0.1:{API_PORT}")
env.setdefault("STREAMLIT_SERVER_PORT", str(UI_PORT))
env.setdefault("STREAMLIT_SERVER_HEADLESS", "true")
env.setdefault("STREAMLIT_BROWSER_GATHERUSAGESTATS", "false")
env.setdefault("STREAMLIT_CONFIG_DIR", str(BASE / ".streamlit"))

API_APP = "app.main:app"
STREAMLIT_ENTRY = BASE / "ui" / "streamlit" / "main_portal.py"

api_proc: subprocess.Popen | None = None
ui_proc: subprocess.Popen | None = None

# -------- Helpers --------
def _port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.2)
        return s.connect_ex(("127.0.0.1", port)) == 0

def _wait_http(url: str, timeout: float = 25.0) -> bool:
    if not urllib:
        # best effort fallback to TCP port check
        start = time.time()
        while time.time() - start < timeout:
            if _port_open(UI_PORT):
                return True
            time.sleep(0.2)
        return False
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as _:
                return True
        except Exception:
            time.sleep(0.3)
    return False

def _open_browser_once():
    import webbrowser
    try:
        webbrowser.open(f"http://127.0.0.1:{UI_PORT}")
    except Exception:
        pass

# -------- Launchers --------
def start_api():
    global api_proc
    if _port_open(API_PORT):
        return
    cmd = [sys.executable, "-m", "uvicorn", API_APP, "--host", "127.0.0.1", "--port", str(API_PORT), "--log-level", "warning"]
    api_proc = subprocess.Popen(cmd, cwd=str(ROOT), env=env)

def start_ui():
    global ui_proc
    if _port_open(UI_PORT):
        return
    cmd = [
        sys.executable, "-m", "streamlit", "run", str(STREAMLIT_ENTRY),
        "--server.port", str(UI_PORT),
        "--server.headless", "true",
        "--server.fileWatcherType", "poll",   # more stable in frozen envs
        "--browser.gatherUsageStats", "false",
    ]
    ui_proc = subprocess.Popen(cmd, cwd=str(ROOT), env=env)

def main():
    # If UI already running, just open a single tab and exit.
    if _port_open(UI_PORT):
        if AUTO_OPEN:
            _open_browser_once()
        sys.exit(0)

    # Start API if needed
    start_api()
    # Give API a head start (UI talks to it on load)
    time.sleep(0.8)

    # Start UI (if port free)
    start_ui()

    # Open one tab after the UI is ready
    if AUTO_OPEN:
        def waiter():
            if _wait_http(f"http://127.0.0.1:{UI_PORT}"):
                _open_browser_once()
        threading.Thread(target=waiter, daemon=True).start()

    # Graceful shutdown
    def shutdown(*_):
        for p in (ui_proc, api_proc):
            try:
                if p and p.poll() is None:
                    p.terminate()
            except Exception:
                pass

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    code = 0
    try:
        if ui_proc:
            code = ui_proc.wait()
    finally:
        if api_proc and api_proc.poll() is None:
            try:
                api_proc.terminate()
                api_proc.wait(timeout=5)
            except Exception:
                pass
    sys.exit(code)

if __name__ == "__main__":
    main()
