"""Native desktop entrypoint for the AstroEngine Windows shell."""

from __future__ import annotations

import logging
import os
import platform
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path
from typing import Any

from .config import DesktopConfigManager, DesktopConfigModel
from .copilot import DesktopCopilot

LOG = logging.getLogger(__name__)


class APIServerController:
    """Manage the bundled uvicorn server lifecycle."""

    def __init__(self, config: DesktopConfigModel) -> None:
        self.host = config.api_host
        self.port = config.api_port
        self.log_level = config.logging_level.lower()
        self._thread: threading.Thread | None = None
        self._server: Any | None = None
        self._lock = threading.Lock()

    def configure(self, config: DesktopConfigModel) -> None:
        restart_needed = (
            self.is_running()
            and (self.host != config.api_host or self.port != config.api_port)
        )
        self.host = config.api_host
        self.port = config.api_port
        self.log_level = config.logging_level.lower()
        if restart_needed:
            self.restart()

    def start(self) -> None:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._thread = threading.Thread(target=self._run_server, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        with self._lock:
            if self._server is not None:
                self._server.should_exit = True
                self._server.force_exit = True
            thread = self._thread
        if thread:
            thread.join(timeout=5)

    def restart(self) -> None:
        self.stop()
        self.start()

    def is_running(self) -> bool:
        thread = self._thread
        return bool(thread and thread.is_alive())

    def _run_server(self) -> None:
        try:
            import uvicorn

            from app.main import app as fastapi_app
        except Exception as exc:  # pragma: no cover - runtime import errors
            LOG.exception("Unable to launch API server: %s", exc)
            return

        config = uvicorn.Config(
            fastapi_app,
            host=self.host,
            port=self.port,
            log_level=self.log_level,
            access_log=False,
        )
        server = uvicorn.Server(config)
        self._server = server
        try:
            server.run()
        except Exception as exc:  # pragma: no cover - uvicorn runtime error
            LOG.exception("uvicorn exited unexpectedly: %s", exc)
        finally:
            self._server = None


class StreamlitController:
    """Launch and monitor the embedded Streamlit UI."""

    def __init__(self, config: DesktopConfigModel, base_dir: Path) -> None:
        self.port = config.streamlit_port
        self.host = "127.0.0.1"
        self.process: subprocess.Popen[bytes] | None = None
        self._lock = threading.Lock()
        self._log_path = base_dir / "logs" / "streamlit.log"
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        self._log_handle: Any | None = None
        self._entry = self._resolve_entry()

    def configure(self, config: DesktopConfigModel) -> None:
        restart_needed = self.is_running() and self.port != config.streamlit_port
        self.port = config.streamlit_port
        if restart_needed:
            self.restart()

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def start(self) -> None:
        with self._lock:
            if self.process and self.process.poll() is None:
                return
            command = [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                str(self._entry),
                "--server.headless",
                "true",
                "--server.port",
                str(self.port),
            ]
            self._log_handle = self._log_path.open("a", encoding="utf-8")
            self.process = subprocess.Popen(
                command,
                stdout=self._log_handle,
                stderr=subprocess.STDOUT,
            )
        self._wait_port(self.host, self.port)

    def stop(self) -> None:
        with self._lock:
            proc = self.process
            self.process = None
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:  # pragma: no cover - fallback cleanup
                proc.kill()
        if self._log_handle is not None:
            try:
                self._log_handle.close()
            except Exception:  # pragma: no cover - defensive cleanup
                pass
            self._log_handle = None

    def restart(self) -> None:
        self.stop()
        self.start()

    def is_running(self) -> bool:
        proc = self.process
        return bool(proc and proc.poll() is None)

    def open_in_browser(self) -> None:
        self.start()
        webbrowser.open(self.url, new=1)

    def _wait_port(self, host: str, port: int, timeout: float = 45.0) -> bool:
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

    def _resolve_entry(self) -> Path:
        bundle_base = Path(getattr(sys, "_MEIPASS", Path.cwd()))
        candidates = [
            bundle_base / "ui" / "streamlit" / "vedic_app.py",
            Path(__file__).resolve().parents[3] / "ui" / "streamlit" / "vedic_app.py",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        raise FileNotFoundError("Unable to locate Streamlit entry point")


class DesktopBridge:
    """Expose desktop automation to pywebview JavaScript bindings."""

    def __init__(self, app: AstroEngineDesktopApp) -> None:
        self.app = app

    # Settings ---------------------------------------------------------
    def get_config(self) -> dict[str, Any]:
        return self.app.config_manager.redact(self.app.config)

    def save_config(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            updated = self.app.config_manager.update(**payload)
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
        self.app.on_config_updated(updated)
        return {"ok": True, "config": self.app.config_manager.redact(updated)}

    def validate_database(self, url: str) -> dict[str, Any]:
        error = self.app.config_manager.probe_database(url)
        return {"ok": error is None, "error": error}

    def check_ephemeris(self, path: str) -> dict[str, Any]:
        ok = self.app.config_manager.check_ephemeris_path(path)
        return {"ok": ok}

    # Copilot ----------------------------------------------------------
    def copilot_status(self) -> dict[str, Any]:
        return self.app.copilot.status()

    def copilot_send(self, message: str) -> dict[str, Any]:
        result = self.app.copilot.send(message)
        return {
            "response": result.response,
            "tokens": result.tokens_consumed,
            "total": result.total_tokens,
            "tools": result.tool_invocations,
        }

    def copilot_tool(self, name: str) -> dict[str, Any]:
        try:
            output = self.app.copilot.invoke_tool(name)
            return {"ok": True, "output": output}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    # Desktop convenience ----------------------------------------------
    def open_logs(self) -> dict[str, Any]:
        try:
            self.app.open_logs()
            return {"ok": True}
        except Exception as exc:  # pragma: no cover - platform specific
            return {"ok": False, "error": str(exc)}

    def issue_bundle(self) -> dict[str, Any]:
        try:
            bundle = self.app.create_issue_bundle()
            return {"ok": True, "path": str(bundle)}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}


class AstroEngineDesktopApp:
    """Top-level orchestrator for the Windows desktop experience."""

    SETTINGS_HTML = (Path(__file__).with_name("settings.html"))
    CHAT_HTML = (Path(__file__).with_name("chat.html"))

    def __init__(self, *, config_manager: DesktopConfigManager | None = None) -> None:
        self.config_manager = config_manager or DesktopConfigManager()
        self.config = self.config_manager.load()
        self.config_manager.apply_environment(self.config)
        self._configure_logging(self.config)
        self.api_controller = APIServerController(self.config)
        self.ui_controller = StreamlitController(self.config, self.config_manager.base_dir)
        self.copilot = DesktopCopilot(self.config_manager)
        self._tray_icon = None
        self._webview_window = None
        self._settings_window = None
        self._chat_window = None
        self._windows: list[Any] = []
        self._shutdown = threading.Event()
        self._health_thread: threading.Thread | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def run(self) -> None:
        self.api_controller.start()
        self.ui_controller.start()
        self._start_tray()
        self._launch_webview()

    def shutdown(self) -> None:
        self._shutdown.set()
        if self._tray_icon is not None:
            try:
                self._tray_icon.stop()
            except Exception:  # pragma: no cover
                pass
        self.ui_controller.stop()
        self.api_controller.stop()

    def on_config_updated(self, config: DesktopConfigModel) -> None:
        self.config = config
        self.config_manager.apply_environment(config)
        self.api_controller.configure(config)
        self.ui_controller.configure(config)
        self.copilot.refresh_config()

    def open_logs(self) -> None:
        path = self.config_manager.log_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch(exist_ok=True)
        if platform.system() == "Windows":  # pragma: no cover - requires Windows
            os.startfile(path)  # type: ignore[attr-defined]
        else:
            try:
                subprocess.Popen(["xdg-open", str(path)])
            except FileNotFoundError:
                subprocess.Popen(["open", str(path)])

    def create_issue_bundle(self) -> Path:
        return self.copilot.create_issue_bundle()

    def open_metrics(self) -> None:
        url = f"http://{self.config.api_host}:{self.config.api_port}/metrics"
        webbrowser.open(url, new=1)

    def open_collector_logs(self) -> None:
        path = self.config_manager.logs_dir / "collector.log"
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text("No collector logs captured yet.\n", encoding="utf-8")
        if platform.system() == "Windows":  # pragma: no cover - requires Windows
            os.startfile(path)  # type: ignore[attr-defined]
        else:
            try:
                subprocess.Popen(["xdg-open", str(path)])
            except FileNotFoundError:
                subprocess.Popen(["open", str(path)])

    def _open_text_document(self, title: str, content: str) -> None:
        safe_title = title.lower().replace(" ", "-")
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        path = self.config_manager.issue_dir / f"{safe_title}-{timestamp}.txt"
        path.write_text(content, encoding="utf-8")
        if platform.system() == "Windows":  # pragma: no cover - requires Windows
            os.startfile(path)  # type: ignore[attr-defined]
        else:
            try:
                subprocess.Popen(["xdg-open", str(path)])
            except FileNotFoundError:
                subprocess.Popen(["open", str(path)])

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _configure_logging(self, config: DesktopConfigModel) -> None:
        log_level = getattr(logging, config.logging_level, logging.INFO)
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        if not any(isinstance(handler, logging.FileHandler) for handler in root_logger.handlers):
            file_handler = logging.FileHandler(self.config_manager.log_path, encoding="utf-8")
            file_handler.setFormatter(
                logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
            )
            root_logger.addHandler(file_handler)

    def _launch_webview(self) -> None:
        try:
            import webview
        except Exception as exc:  # pragma: no cover - dependency missing
            LOG.warning("pywebview unavailable (%s); falling back to browser", exc)
            self.ui_controller.open_in_browser()
            self._wait_forever()
            return

        bridge = DesktopBridge(self)
        menu = self._build_menu(webview)
        window = webview.create_window(
            "AstroEngine",
            url=self.ui_controller.url,
            width=1280,
            height=800,
            resizable=True,
            text_select=True,
            js_api=bridge,
            menu=menu,
        )
        self._settings_window = webview.create_window(
            "Settings",
            html=DEFAULT_SETTINGS_HTML,
            width=720,
            height=780,
            js_api=bridge,
            hidden=True,
            resizable=True,
        )
        self._chat_window = webview.create_window(
            "AstroEngine Copilot",
            html=DEFAULT_CHAT_HTML,
            width=520,
            height=720,
            js_api=bridge,
            hidden=True,
            resizable=True,
        )
        self._webview_window = window
        for w in (window, self._settings_window, self._chat_window):
            if w is not None:
                self._windows.append(w)
        gui = "edgechromium" if platform.system() == "Windows" else None
        try:
            webview.start(self._on_webview_ready, window=window, gui=gui)
        finally:
            self.shutdown()

    def _build_menu(self, webview: Any) -> Any:
        try:
            from webview import menu as menu_module
        except Exception:
            return None

        def item(title: str, callback: Any) -> Any:
            return menu_module.MenuItem(title, callback)

        return menu_module.Menu(
            menu_module.MenuItem(
                "AstroEngine",
                [
                    item("Start API", lambda: self.api_controller.start()),
                    item("Stop API", lambda: self.api_controller.stop()),
                    item("Open UI in browser", lambda: self.ui_controller.open_in_browser()),
                    item("Diagnostics", lambda: self._open_text_document("Diagnostics", self.copilot.invoke_tool("diagnostics"))),
                    item("Open Logs", lambda: self.open_logs()),
                    item("Open Metrics", lambda: self.open_metrics()),
                    item("Collector Logs", lambda: self.open_collector_logs()),
                    item("Settings", lambda: self._open_settings()),
                    item("Chat Copilot", lambda: self._open_chat()),
                    item("Quit", lambda: self.shutdown()),
                ],
            )
        )

    def _on_webview_ready(self) -> None:
        self._start_health_monitor()

    def _start_tray(self) -> None:
        try:
            import pystray
            from PIL import Image, ImageDraw
        except Exception as exc:  # pragma: no cover - optional dependency missing
            LOG.info("System tray unavailable: %s", exc)
            return

        image = Image.new("RGB", (64, 64), color="#1b2352")
        draw = ImageDraw.Draw(image)
        draw.ellipse((12, 12, 52, 52), fill="#c9973b")
        menu = pystray.Menu(
            pystray.MenuItem("Start API", lambda: self.api_controller.start()),
            pystray.MenuItem("Stop API", lambda: self.api_controller.stop()),
            pystray.MenuItem("Open UI", lambda: self.ui_controller.open_in_browser()),
            pystray.MenuItem("Diagnostics", lambda: self._open_text_document("Diagnostics", self.copilot.invoke_tool("diagnostics"))),
            pystray.MenuItem("Open Logs", lambda: self.open_logs()),
            pystray.MenuItem("Open Metrics", lambda: self.open_metrics()),
            pystray.MenuItem("Collector Logs", lambda: self.open_collector_logs()),
            pystray.MenuItem("Settings", lambda: self._open_settings()),
            pystray.MenuItem("Chat Copilot", lambda: self._open_chat()),
            pystray.MenuItem("Quit", lambda: self.shutdown()),
        )
        self._tray_icon = pystray.Icon("astroengine", image, "AstroEngine", menu)
        threading.Thread(target=self._tray_icon.run, daemon=True).start()

    def _start_health_monitor(self) -> None:
        if self._health_thread and self._health_thread.is_alive():
            return

        def poll() -> None:
            last_status: bool | None = None
            while not self._shutdown.is_set():
                status = self._check_api_health()
                if status != last_status:
                    for window in list(self._windows):
                        if window is None:
                            continue
                        try:
                            window.evaluate_js(
                                "window.AstroEngine?.setApiStatus?.(" + ("true" if status else "false") + ")"
                            )
                        except Exception:  # pragma: no cover - JS errors ignored
                            LOG.debug("Failed to push health status to webview", exc_info=True)
                last_status = status
                time.sleep(5)

        self._health_thread = threading.Thread(target=poll, daemon=True)
        self._health_thread.start()

    def _check_api_health(self) -> bool:
        try:
            import httpx

            url = f"http://{self.config.api_host}:{self.config.api_port}/healthz"
            with httpx.Client(timeout=3.0) as client:
                response = client.get(url)
                response.raise_for_status()
            return True
        except Exception:
            return False

    def _open_settings(self) -> None:
        if self._settings_window is not None:
            self._settings_window.show()
            try:
                self._settings_window.focus()
            except Exception:  # pragma: no cover - GUI dependent
                pass

    def _open_chat(self) -> None:
        if self._chat_window is not None:
            self._chat_window.show()
            try:
                self._chat_window.focus()
            except Exception:  # pragma: no cover - GUI dependent
                pass

    def _wait_forever(self) -> None:
        try:
            while not self._shutdown.is_set():
                time.sleep(1)
        except KeyboardInterrupt:
            self.shutdown()


DEFAULT_SETTINGS_HTML = """<!DOCTYPE html>
<html lang=\"en\">
<head>
<meta charset=\"utf-8\" />
<title>AstroEngine Settings</title>
<style>
body { font-family: 'Segoe UI', sans-serif; margin: 0; padding: 1.5rem; background: #101321; color: #f5f6fa; }
form { max-width: 720px; margin: 0 auto; }
label { display: block; margin-top: 1rem; font-weight: 600; }
input, select { width: 100%; padding: 0.5rem; border-radius: 6px; border: 1px solid #2d3256; background: #1b2040; color: #f5f6fa; }
input:focus-visible, select:focus-visible, button:focus-visible { outline: 2px solid #ffd166; outline-offset: 2px; }
button { margin-top: 1.5rem; padding: 0.6rem 1.2rem; border: none; border-radius: 6px; background: #c9973b; color: #101321; font-weight: 600; cursor: pointer; }
button.secondary { background: transparent; border: 1px solid #c9973b; color: #c9973b; margin-left: 0.5rem; }
#status { margin-top: 1rem; min-height: 1.5rem; }
</style>
</head>
<body>
<h1>AstroEngine Settings</h1>
<form id=\"settingsForm\" onsubmit=\"return false;\">
  <label>Database URL <input name=\"database_url\" required /></label>
  <label>Swiss Ephemeris Path <input name=\"se_ephe_path\" placeholder=\"C:/SwissEphemeris\" /></label>
  <label>API Host <input name=\"api_host\" required /></label>
  <label>API Port <input name=\"api_port\" type=\"number\" min=\"1\" max=\"65535\" required /></label>
  <label>Streamlit Port <input name=\"streamlit_port\" type=\"number\" min=\"1\" max=\"65535\" required /></label>
  <label>AE_QCACHE_SEC <input name=\"qcache_sec\" type=\"number\" step=\"0.1\" min=\"0.01\" /></label>
  <label>AE_QCACHE_SIZE <input name=\"qcache_size\" type=\"number\" min=\"128\" /></label>
  <label>Logging Level
    <select name=\"logging_level\">
      <option>DEBUG</option>
      <option>INFO</option>
      <option>WARNING</option>
      <option>ERROR</option>
      <option>CRITICAL</option>
    </select>
  </label>
  <label>Theme
    <select name=\"theme\">
      <option value=\"system\">System</option>
      <option value=\"light\">Light</option>
      <option value=\"dark\">Dark</option>
      <option value=\"high_contrast\">High Contrast</option>
    </select>
  </label>
  <label>OpenAI API Key <input name=\"openai_api_key\" type=\"password\" autocomplete=\"off\" /></label>
  <label>OpenAI Model <input name=\"openai_model\" /></label>
  <label>OpenAI Base URL <input name=\"openai_base_url\" /></label>
  <label>Copilot Daily Limit <input name=\"copilot_daily_limit\" type=\"number\" min=\"0\" /></label>
  <label>Copilot Session Limit <input name=\"copilot_session_limit\" type=\"number\" min=\"0\" /></label>
  <label><input type=\"checkbox\" name=\"autostart\" /> Start AstroEngine when I sign in</label>
  <div style=\"display:flex; gap:0.5rem; flex-wrap:wrap;\">
    <button id=\"saveButton\">Save Settings</button>
    <button class=\"secondary\" id=\"testDb\">Test Database</button>
    <button class=\"secondary\" id=\"checkEphe\">Check Ephemeris Path</button>
    <button class=\"secondary\" id=\"makeBundle\">Create Issue Bundle</button>
  </div>
</form>
<div id=\"status\" role=\"status\" aria-live=\"polite\"></div>
<script>
const form = document.getElementById('settingsForm');
const statusEl = document.getElementById('status');
const dbBtn = document.getElementById('testDb');
const epheBtn = document.getElementById('checkEphe');
const bundleBtn = document.getElementById('makeBundle');

function showStatus(message, ok=true) {
  statusEl.textContent = message;
  statusEl.style.color = ok ? '#7fffd4' : '#ff6b6b';
}

function formData() {
  const data = new FormData(form);
  const payload = {};
  for (const [key, value] of data.entries()) {
    if (key === 'autostart') {
      payload[key] = form.autostart.checked;
    } else if (['api_port', 'streamlit_port', 'qcache_size', 'copilot_daily_limit', 'copilot_session_limit'].includes(key)) {
      payload[key] = value ? Number(value) : 0;
    } else if (key === 'qcache_sec') {
      payload[key] = Number(value);
    } else {
      payload[key] = value;
    }
  }
  return payload;
}

async function load() {
  const cfg = await window.pywebview.api.get_config();
  for (const [key, value] of Object.entries(cfg)) {
    if (form[key] === undefined) continue;
    if (typeof form[key].type === 'string' && form[key].type === 'checkbox') {
      form[key].checked = Boolean(value);
    } else {
      form[key].value = value ?? '';
    }
  }
  showStatus('Configuration loaded', true);
}

form.addEventListener('submit', async () => {
  const payload = formData();
  const result = await window.pywebview.api.save_config(payload);
  if (result.ok) {
    showStatus('Saved. Services restarting with new configuration.');
  } else {
    showStatus(result.error, false);
  }
});

dbBtn.addEventListener('click', async () => {
  const payload = formData();
  const result = await window.pywebview.api.validate_database(payload.database_url);
  if (result.ok) {
    showStatus('Database connection succeeded.');
  } else {
    showStatus(result.error, false);
  }
});

epheBtn.addEventListener('click', async () => {
  const payload = formData();
  const result = await window.pywebview.api.check_ephemeris(payload.se_ephe_path);
  if (result.ok) {
    showStatus('Swiss Ephemeris path verified.');
  } else {
    showStatus('Swiss Ephemeris path not found.', false);
  }
});

bundleBtn.addEventListener('click', async () => {
  const result = await window.pywebview.api.issue_bundle();
  if (result.ok) {
    showStatus('Issue bundle created at ' + result.path);
  } else {
    showStatus(result.error, false);
  }
});

window.AstroEngine = window.AstroEngine || {};
window.AstroEngine.setApiStatus = function(online) {
  document.body.style.borderTop = online ? '4px solid #0f9960' : '4px solid #ff6b6b';
};

load();
</script>
</body>
</html>
"""


DEFAULT_CHAT_HTML = """<!DOCTYPE html>
<html lang=\"en\">
<head>
<meta charset=\"utf-8\" />
<title>AstroEngine Copilot</title>
<style>
body { font-family: 'Segoe UI', sans-serif; margin: 0; padding: 1rem; background: #0f1224; color: #f5f6fa; }
#messages { max-height: 520px; overflow-y: auto; padding: 0.5rem; border: 1px solid #272a4b; border-radius: 8px; background: #141836; }
.message { margin-bottom: 1rem; padding: 0.6rem 0.75rem; border-radius: 6px; }
.message.user { background: #1e2344; border-left: 3px solid #c9973b; }
.message.assistant { background: #16294f; border-left: 3px solid #0f9960; }
#composer { display: flex; gap: 0.5rem; margin-top: 1rem; }
#composer textarea { flex: 1; min-height: 60px; border-radius: 6px; border: 1px solid #2d3256; background: #1b2040; color: #f5f6fa; padding: 0.5rem; }
#composer button { padding: 0.6rem 1rem; border: none; border-radius: 6px; background: #c9973b; color: #101321; font-weight: 600; cursor: pointer; }
#status { margin-top: 0.5rem; font-size: 0.85rem; color: #9aa5ff; }
</style>
</head>
<body>
<h1>AstroEngine Copilot</h1>
<div id=\"messages\"></div>
<div id=\"status\"></div>
<form id=\"composer\">
  <textarea id=\"prompt\" placeholder=\"Ask the copilot to run diagnostics, tail logs, or explain an endpoint...\"></textarea>
  <button>Send</button>
</form>
<script>
const messagesEl = document.getElementById('messages');
const statusEl = document.getElementById('status');
const composer = document.getElementById('composer');
const promptEl = document.getElementById('prompt');

function append(role, text) {
  const div = document.createElement('div');
  div.className = 'message ' + role;
  div.innerHTML = '<strong>' + role + '</strong><br />' + text.replace(/\n/g, '<br />');
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

async function refreshStatus() {
  const stats = await window.pywebview.api.copilot_status();
  statusEl.textContent = `Tokens today: ${stats.tokens_used_today}/${stats.daily_limit} · API ${stats.client_available ? 'ready' : 'not configured'}`;
}

composer.addEventListener('submit', async (event) => {
  event.preventDefault();
  const text = promptEl.value.trim();
  if (!text) return;
  append('user', text);
  promptEl.value = '';
  append('assistant', '… running tools / awaiting response …');
  const nodes = messagesEl.querySelectorAll('.message.assistant');
  const placeholder = nodes[nodes.length - 1];
  const result = await window.pywebview.api.copilot_send(text);
  placeholder.innerHTML = '<strong>assistant</strong><br />' + result.response.replace(/\n/g, '<br />');
  refreshStatus();
});

window.AstroEngine = window.AstroEngine || {};
window.AstroEngine.setApiStatus = function(online) {
  statusEl.style.borderBottom = online ? '3px solid #0f9960' : '3px solid #ff6b6b';
};

refreshStatus();
</script>
</body>
</html>
"""


__all__ = ["AstroEngineDesktopApp", "APIServerController", "StreamlitController"]
