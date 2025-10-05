"""ChatGPT copilot integration for the AstroEngine desktop shell."""

from __future__ import annotations

import datetime as _dt
import json
import logging
import re
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import httpx

from astroengine import diagnostics
from astroengine.narrative.gpt_api import GPTNarrativeClient

from .config import DesktopConfigManager

LOG = logging.getLogger(__name__)

_TOOL_HINTS = {
    "diagnostics": ("diagnostic", "doctor", "health check"),
    "healthz": ("healthz", "health", "status"),
    "tail_logs": ("tail log", "recent log", "show log"),
    "summarize_errors": ("error summary", "explain error"),
    "explain_endpoints": ("explain endpoint", "api list", "help endpoint"),
}

_SECRET_PATTERN = re.compile(r"(?<=://)([^:@]+):([^@]+)@")


@dataclass
class CopilotMessage:
    role: str
    content: str


@dataclass
class CopilotResult:
    response: str
    tokens_consumed: int
    total_tokens: int
    tool_invocations: list[str]


class DesktopCopilot:
    """Simple assistant wrapper that routes tool requests and GPT completions."""

    def __init__(
        self,
        config_manager: DesktopConfigManager,
        *,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.config_manager = config_manager
        self.http_client = http_client or httpx.Client(timeout=10.0)
        self.state_path = self.config_manager.base_dir / "copilot_state.json"
        self.messages: list[CopilotMessage] = []
        self._state_lock = threading.Lock()
        self._daily_tokens, self._state_date = self._load_token_state()
        self.config = self.config_manager.load()
        self.client = GPTNarrativeClient(
            api_key=self.config.openai_api_key or None,
            model=self.config.openai_model,
            base_url=self.config.openai_base_url or None,
            allow_stub=True,
        )

    # ------------------------------------------------------------------
    # High level conversation API
    # ------------------------------------------------------------------
    def refresh_config(self) -> None:
        """Reload configuration (e.g., after settings change)."""

        with self._state_lock:
            self.config = self.config_manager.load()
            self.client = GPTNarrativeClient(
                api_key=self.config.openai_api_key or None,
                model=self.config.openai_model,
                base_url=self.config.openai_base_url or None,
                allow_stub=True,
            )

    def send(self, user_text: str) -> CopilotResult:
        """Process ``user_text`` and return a response."""

        user_text = user_text.strip()
        if not user_text:
            return CopilotResult("I need a question to help with.", 0, self._daily_tokens, [])

        today = _dt.date.today()
        with self._state_lock:
            if today != self._state_date:
                self._daily_tokens = 0
                self._state_date = today
            if (
                self.config.copilot_daily_limit
                and self._daily_tokens >= self.config.copilot_daily_limit
            ):
                return CopilotResult(
                    "The daily copilot token budget has been reached. Try again tomorrow or raise the limit in Settings.",
                    0,
                    self._daily_tokens,
                    [],
                )

        self.messages.append(CopilotMessage("user", user_text))
        tools = self._detect_tools(user_text)
        tool_outputs: list[str] = []
        tool_names: list[str] = []
        for tool_name in tools:
            try:
                output = self._invoke_tool(tool_name)
            except Exception as exc:  # pragma: no cover - runtime safety
                LOG.exception("Tool %s failed", tool_name)
                output = f"{tool_name} failed: {exc}"
            sanitized = self._sanitize(output)
            tool_outputs.append(f"[{tool_name}]\n{sanitized}")
            tool_names.append(tool_name)

        prompt = self._build_prompt(user_text, tool_outputs)
        if not self.client.available:
            response_text = self._fallback_response(user_text, tool_outputs)
            tokens = self._estimate_tokens(response_text)
            self._record_tokens(tokens)
            self.messages.append(CopilotMessage("assistant", response_text))
            return CopilotResult(response_text, tokens, self._daily_tokens, tool_names)

        try:
            response_text = self.client.summarize(prompt)
        except Exception as exc:  # pragma: no cover - network error
            LOG.warning("OpenAI request failed: %s", exc)
            response_text = self._fallback_response(user_text, tool_outputs)
        tokens = self._estimate_tokens(response_text)
        self._record_tokens(tokens)
        response_text = self._sanitize(response_text)
        self.messages.append(CopilotMessage("assistant", response_text))
        return CopilotResult(response_text, tokens, self._daily_tokens, tool_names)

    def status(self) -> dict[str, Any]:
        """Return telemetry for UI bindings (tokens and key availability)."""

        return {
            "tokens_used_today": self._daily_tokens,
            "daily_limit": self.config.copilot_daily_limit,
            "session_limit": self.config.copilot_session_limit,
            "client_available": self.client.available,
        }

    def invoke_tool(self, name: str) -> str:
        """Expose tool invocation for the settings UI (with sanitisation)."""

        output = self._invoke_tool(name)
        return self._sanitize(output)

    def create_issue_bundle(self) -> Path:
        """Create a support bundle and return the resulting archive path."""

        return self._create_issue_bundle()

    # ------------------------------------------------------------------
    # Tool routing
    # ------------------------------------------------------------------
    def _detect_tools(self, message: str) -> list[str]:
        message_lower = message.lower()
        matches: list[str] = []
        for name, keywords in _TOOL_HINTS.items():
            if any(keyword in message_lower for keyword in keywords):
                matches.append(name)
        if "issue" in message_lower and "report" in message_lower:
            matches.append("issue_bundle")
        return matches

    def _invoke_tool(self, name: str) -> str:
        if name == "diagnostics":
            return self._run_diagnostics()
        if name == "healthz":
            return self._fetch_healthz()
        if name == "tail_logs":
            return self._tail_logs()
        if name == "summarize_errors":
            return self._summarize_errors()
        if name == "explain_endpoints":
            return self._explain_endpoints()
        if name == "issue_bundle":
            bundle = self._create_issue_bundle()
            return f"Issue bundle prepared at: {bundle}"
        raise ValueError(f"Unknown tool '{name}'")

    def _run_diagnostics(self) -> str:
        checks = [diagnostics.check_python()]
        for func in (
            diagnostics.check_core_imports,
            diagnostics.check_optional_deps,
            diagnostics.check_timezone_libs,
            diagnostics.check_swisseph,
        ):
            results = func()
            if isinstance(results, diagnostics.Check):
                checks.append(results)
            else:
                checks.extend(results)
        ordered = sorted(checks, key=lambda chk: diagnostics._status_order(chk.status))
        lines = ["AstroEngine diagnostics:"]
        for chk in ordered:
            detail = chk.detail.strip()
            lines.append(f"- [{chk.status}] {chk.name}: {detail}")
        return "\n".join(lines)

    def _fetch_healthz(self) -> str:
        url = f"http://{self.config.api_host}:{self.config.api_port}/healthz"
        try:
            response = self.http_client.get(url)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as exc:
            return f"Failed to reach {url}: {exc}"
        return json.dumps(data, indent=2, sort_keys=True)

    def _tail_logs(self, limit: int = 200) -> str:
        path = self.config_manager.log_path
        if not path.exists():
            return "No log file has been written yet."
        from collections import deque

        tail = deque(maxlen=limit)
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            for line in handle:
                tail.append(line.rstrip("\n"))
        sanitized = [self._sanitize(line) for line in tail]
        return "\n".join(sanitized)

    def _summarize_errors(self) -> str:
        text = self._tail_logs(limit=400)
        errors = [line for line in text.splitlines() if "ERROR" in line]
        if not errors:
            return "No recent ERROR lines captured in the log tail."
        summary = ["Recent error lines:"]
        summary.extend(errors[-25:])
        return "\n".join(summary)

    def _explain_endpoints(self) -> str:
        url = f"http://{self.config.api_host}:{self.config.api_port}/openapi.json"
        try:
            response = self.http_client.get(url)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as exc:
            return f"Failed to query {url}: {exc}"
        paths = data.get("paths", {}) if isinstance(data, dict) else {}
        lines = ["Available API endpoints:"]
        for path, methods in sorted(paths.items()):
            if not isinstance(methods, dict):
                continue
            verbs = ", ".join(sorted(methods))
            lines.append(f"- {path} ({verbs})")
        return "\n".join(lines)

    def _create_issue_bundle(self) -> Path:
        timestamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        diagnostics_text = self._run_diagnostics()
        logs_text = self._tail_logs(limit=500)
        payload = {
            "generated_at": _dt.datetime.now().isoformat(),
            "diagnostics": diagnostics_text,
            "log_tail": logs_text,
        }
        metadata_path = self.config_manager.ensure_issue_bundle(f"bundle-{timestamp}", payload)
        archive_path = self.config_manager.issue_dir / f"astroengine-support-{timestamp}.zip"
        from zipfile import ZIP_DEFLATED, ZipFile

        with ZipFile(archive_path, "w", ZIP_DEFLATED) as archive:
            archive.writestr("diagnostics.txt", diagnostics_text)
            archive.writestr("logs.txt", logs_text)
            archive.write(metadata_path, metadata_path.name)
        return archive_path

    # ------------------------------------------------------------------
    # State helpers
    # ------------------------------------------------------------------
    def _build_prompt(self, user_text: str, tool_outputs: Iterable[str]) -> str:
        parts = [
            "You are AstroEngine's desktop copilot. Always cite actual diagnostics data.",
            "User question:",
            user_text,
        ]
        for output in tool_outputs:
            parts.append("Tool output:")
            parts.append(output)
        parts.append(
            "Explain the findings with concrete references. If you lack data, ask the user to run a relevant tool."
        )
        return "\n\n".join(parts)

    def _fallback_response(self, user_text: str, tool_outputs: list[str]) -> str:
        if tool_outputs:
            joined = "\n\n".join(tool_outputs)
            return (
                "I summarised the requested tools locally because the OpenAI client is not configured.\n"
                f"Here is the raw output:\n{joined}"
            )
        return (
            "The OpenAI client is not configured. Add an API key under Settings to enable natural language responses."
        )

    def _sanitize(self, text: str) -> str:
        secrets: list[str] = []
        if self.config.openai_api_key:
            secrets.append(self.config.openai_api_key)
        secrets.append(self.config.database_url)
        for secret in secrets:
            if secret:
                text = text.replace(secret, "[redacted]")
        text = _SECRET_PATTERN.sub(lambda m: f"{m.group(1)}:[redacted]@", text)
        return text

    def _estimate_tokens(self, text: str) -> int:
        words = len(text.split())
        return max(1, int(words * 1.3))

    def _record_tokens(self, tokens: int) -> None:
        with self._state_lock:
            session_limit = self.config.copilot_session_limit
            if session_limit and tokens > session_limit:
                tokens = session_limit
            self._daily_tokens += tokens
            self._save_token_state()

    def _load_token_state(self) -> tuple[int, _dt.date]:
        if not self.state_path.exists():
            return 0, _dt.date.today()
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
            stored_date = _dt.date.fromisoformat(data.get("date", ""))
            tokens = int(data.get("tokens", 0))
            today = _dt.date.today()
            if stored_date == today:
                return tokens, stored_date
        except Exception as exc:  # pragma: no cover - best effort load
            LOG.debug("Unable to load copilot state: %s", exc)
        return 0, _dt.date.today()

    def _save_token_state(self) -> None:
        payload = {"date": self._state_date.isoformat(), "tokens": self._daily_tokens}
        try:
            self.state_path.write_text(json.dumps(payload), encoding="utf-8")
        except Exception as exc:  # pragma: no cover - filesystem errors
            LOG.debug("Unable to persist copilot state: %s", exc)


__all__ = ["DesktopCopilot", "CopilotResult", "CopilotMessage"]
