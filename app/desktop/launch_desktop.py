from __future__ import annotations

import os
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

APP_NAME = "AstroEngine"
LOCAL_APPDATA = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / ".astroengine")))
APP_HOME = LOCAL_APPDATA / APP_NAME
APP_HOME.mkdir(parents=True, exist_ok=True)

os.environ.setdefault("ASTROENGINE_HOME", str(APP_HOME))
os.environ.setdefault("DATABASE_URL", f"sqlite:///{(APP_HOME / 'dev.db').as_posix()}")

CONFIG_PATH = APP_HOME / "config.yaml"
if CONFIG_PATH.exists():
    try:
        import yaml

        cfg = yaml.safe_load(CONFIG_PATH.read_text()) or {}
        se_path = cfg.get("SE_EPHE_PATH")
        if se_path:
            os.environ["SE_EPHE_PATH"] = str(se_path)
    except Exception:  # pragma: no cover - defensive logging for desktop runtime
        pass
else:
    CONFIG_PATH.write_text(
        """# AstroEngine Desktop config\n# Set to your Swiss Ephemeris data folder if you have it\n# SE_EPHE_PATH: C:/path/to/sweph\n"""
    )

BUNDLE_BASE = Path(getattr(sys, "_MEIPASS", Path.cwd()))
MIGRATIONS_DIR = BUNDLE_BASE / "migrations"
ALEMBIC_INI = BUNDLE_BASE / "alembic.ini"
UI_ENTRY = BUNDLE_BASE / "ui" / "streamlit" / "vedic_app.py"


def run_migrations() -> None:
    try:
        from alembic import command
        from alembic.config import Config

        cfg = Config(str(ALEMBIC_INI))
        cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
        cfg.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])
        command.upgrade(cfg, "head")
    except Exception as exc:  # pragma: no cover - migrate best effort for desktop runtime
        print(f"[WARN] Migrations failed: {exc}")


def wait_port(host: str, port: int, timeout: float = 30.0) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        with socket.socket() as sock:
            sock.settimeout(0.5)
            try:
                sock.connect((host, port))
                return True
            except OSError:
                time.sleep(0.2)
    return False


def start_api() -> None:
    import uvicorn
    from app.main import app

    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")


def start_ui() -> subprocess.Popen[bytes]:
    ui_path = str(UI_ENTRY)
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        ui_path,
        "--server.headless",
        "true",
        "--server.port",
        "8501",
    ]
    return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


if __name__ == "__main__":
    print(f"[INFO] Home: {APP_HOME}")
    run_migrations()

    api_thread = threading.Thread(target=start_api, daemon=True)
    api_thread.start()
    if not wait_port("127.0.0.1", 8000, 30):
        print("[ERROR] API did not start on 127.0.0.1:8000")

    ui_proc = start_ui()
    if wait_port("127.0.0.1", 8501, 45):
        webbrowser.open("http://127.0.0.1:8501", new=1)
    else:
        print("[WARN] UI did not start on time; check logs.")

    try:
        if ui_proc and ui_proc.stdout:
            for _ in range(500):
                line = ui_proc.stdout.readline()
                if not line:
                    break
                print(line.decode(errors="ignore"), end="")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        if ui_proc:
            try:
                ui_proc.terminate()
            except Exception:
                pass
