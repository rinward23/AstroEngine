"""Entry point used by Windows shortcuts to orchestrate AstroEngine launchers."""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
import webbrowser
from collections.abc import Sequence
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen


DEFAULT_API_HOST = "127.0.0.1"
DEFAULT_API_PORT = 8000
DEFAULT_UI_PORT = 8501
DEFAULT_UI_HOST = "127.0.0.1"
PID_API = "api.pid"
PID_UI = "ui.pid"
HEALTH_PATH = "/health"


class LaunchError(RuntimeError):
    """Raised when one of the launcher stages fails."""


def _bundle_root() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parents[1]


def _var_dir() -> Path:
    root = _bundle_root()
    target = root / "var"
    target.mkdir(parents=True, exist_ok=True)
    return target


def _pid_file(name: str) -> Path:
    pid_root = _var_dir() / "run"
    pid_root.mkdir(parents=True, exist_ok=True)
    return pid_root / name


def _resolve_streamlit_script() -> Path:
    base = _bundle_root()
    candidates = [
        base / "ui" / "streamlit" / "altaz_app.py",
        base / "ui" / "streamlit" / "main_portal.py",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError("Streamlit portal script not found in the installation bundle.")


def _default_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")
    return env


def _creation_flags() -> int:
    if os.name == "nt":
        CREATE_NO_WINDOW = 0x08000000
        return CREATE_NO_WINDOW
    return 0


def _is_process_alive(pid: int) -> bool:
    try:
        if pid <= 0:
            return False
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _read_pid(name: str) -> int | None:
    pid_path = _pid_file(name)
    if not pid_path.exists():
        return None
    try:
        return int(pid_path.read_text().strip())
    except ValueError:
        pid_path.unlink(missing_ok=True)
        return None


def _store_pid(name: str, pid: int) -> None:
    pid_path = _pid_file(name)
    pid_path.write_text(str(pid), encoding="utf-8")


def _remove_pid(name: str) -> None:
    _pid_file(name).unlink(missing_ok=True)


def _wait_for_http(url: str, timeout: float, interval: float = 1.0) -> None:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with urlopen(url, timeout=interval) as response:  # noqa: S310 - localhost request
                if 200 <= response.status < 300:
                    return
        except URLError as error:  # pragma: no cover - network failure path
            last_error = error
        time.sleep(interval)
    if last_error is not None:
        raise LaunchError(f"Timed out waiting for {url}: {last_error}")
    raise LaunchError(f"Timed out waiting for {url}")


def _start_process(args: Sequence[str], *, env: dict[str, str]) -> subprocess.Popen[Any]:
    process = subprocess.Popen(
        list(args),
        env=env,
        cwd=_bundle_root(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=_creation_flags(),
        text=False,
    )
    return process


def _uvicorn_command(host: str, port: int) -> list[str]:
    return [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        host,
        "--port",
        str(port),
    ]


def _streamlit_command(script: Path, host: str, port: int) -> list[str]:
    return [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(script),
        "--server.address",
        host,
        "--server.port",
        str(port),
        "--server.headless",
        "true",
        "--browser.gatherUsageStats",
        "false",
    ]


def _api_port() -> int:
    return int(os.environ.get("ASTROENGINE_API_PORT", DEFAULT_API_PORT))


def _api_host() -> str:
    return os.environ.get("ASTROENGINE_API_HOST", DEFAULT_API_HOST)


def _ui_port() -> int:
    return int(os.environ.get("ASTROENGINE_UI_PORT", DEFAULT_UI_PORT))


def _ui_host() -> str:
    return os.environ.get("ASTROENGINE_UI_HOST", DEFAULT_UI_HOST)


def _open_browser(port: int, host: str) -> None:
    url = f"http://{host}:{port}/"
    webbrowser.open(url)


def _start_api(env: dict[str, str]) -> int:
    existing = _read_pid(PID_API)
    if existing and _is_process_alive(existing):
        return existing
    command = _uvicorn_command(_api_host(), _api_port())
    process = _start_process(command, env=env)
    _store_pid(PID_API, process.pid)
    return process.pid


def _start_ui(env: dict[str, str]) -> int:
    existing = _read_pid(PID_UI)
    if existing and _is_process_alive(existing):
        return existing
    script = _resolve_streamlit_script()
    command = _streamlit_command(script, _ui_host(), _ui_port())
    process = _start_process(command, env=env)
    _store_pid(PID_UI, process.pid)
    return process.pid


def _stop_process(name: str) -> bool:
    pid = _read_pid(name)
    if not pid:
        return False
    if not _is_process_alive(pid):
        _remove_pid(name)
        return False
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        _remove_pid(name)
        return False
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if not _is_process_alive(pid):
            break
        time.sleep(0.5)
    _remove_pid(name)
    return True


def _health_url() -> str:
    return f"http://{_api_host()}:{_api_port()}{HEALTH_PATH}"


def _ui_url() -> str:
    return f"http://{_ui_host()}:{_ui_port()}"


def _status() -> dict[str, Any]:
    return {
        "api": {
            "pid": _read_pid(PID_API),
            "port": _api_port(),
            "host": _api_host(),
        },
        "ui": {
            "pid": _read_pid(PID_UI),
            "port": _ui_port(),
            "host": _ui_host(),
        },
    }


def launch(mode: str, *, open_browser: bool, wait: bool, timeout: float) -> None:
    env = _default_env()

    if mode in {"api", "both"}:
        _start_api(env)
        _wait_for_http(_health_url(), timeout)

    if mode in {"ui", "both"}:
        if mode == "ui":
            _wait_for_http(_health_url(), timeout)
        _start_ui(env)
        _wait_for_http(_ui_url(), timeout)
        if open_browser:
            _open_browser(_ui_port(), _ui_host())
    elif mode == "api" and open_browser:
        _open_browser(_api_port(), _api_host())

    if wait:
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass


def stop(mode: str) -> None:
    if mode in {"api", "both"}:
        _stop_process(PID_API)
    if mode in {"ui", "both"}:
        _stop_process(PID_UI)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AstroEngine Windows launcher helper")
    parser.add_argument(
        "--launch",
        choices=("api", "ui", "both"),
        default="both",
        help="Choose which components to start.",
    )
    parser.add_argument(
        "--stop",
        action="store_true",
        help="Terminate the tracked AstroEngine processes instead of starting them.",
    )
    parser.add_argument(
        "--open-browser/--no-browser",
        dest="open_browser",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Open the default browser once the UI is ready.",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Keep the launcher running after startup until interrupted.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=90.0,
        help="Seconds to wait for each service to report healthy.",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Print process status JSON and exit.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    if args.status:
        print(json.dumps(_status(), indent=2))
        return 0

    try:
        if args.stop:
            stop(args.launch)
        else:
            launch(args.launch, open_browser=args.open_browser, wait=args.wait, timeout=args.timeout)
    except LaunchError as error:
        print(f"AstroEngine launcher error: {error}", file=sys.stderr)
        return 2
    except FileNotFoundError as error:
        print(str(error), file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
