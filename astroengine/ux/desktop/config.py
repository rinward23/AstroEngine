"""Configuration helpers for the AstroEngine desktop shell."""

from __future__ import annotations

import json
import logging
import os
import platform
import sys
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

LOG = logging.getLogger(__name__)

APP_NAME = "AstroEngine"
CONFIG_FILENAME = "config.yaml"
STREAMLIT_DIRNAME = ".streamlit"
STREAMLIT_CONFIG = "config.toml"
DEFAULT_DB_NAME = "astroengine-desktop.db"
DEFAULT_LOG_NAME = "astroengine.log"

_VALID_LOG_LEVELS = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"}
_VALID_THEMES = {"system", "light", "dark", "high_contrast"}


class DesktopConfigModel(BaseModel):
    """Pydantic model describing persisted desktop settings."""

    schema_version: int = Field(default=1, ge=1)
    database_url: str
    se_ephe_path: str = ""
    api_host: str = Field(default="127.0.0.1")
    api_port: int = Field(default=8000, ge=1, le=65535)
    streamlit_port: int = Field(default=8501, ge=1, le=65535)
    qcache_sec: float = Field(default=1.0, gt=0.0)
    qcache_size: int = Field(default=4096, ge=128)
    logging_level: str = Field(default="INFO")
    theme: str = Field(default="system")
    openai_api_key: str = ""
    openai_model: str = Field(default="gpt-4o-mini")
    openai_base_url: str | None = None
    copilot_daily_limit: int = Field(default=50000, ge=0)
    copilot_session_limit: int = Field(default=8000, ge=0)
    autostart: bool = False
    issue_report_dir: str | None = None

    model_config = ConfigDict(extra="allow")

    @field_validator("logging_level")
    @classmethod
    def _validate_logging_level(cls, value: str) -> str:
        level = value.upper().strip()
        if level not in _VALID_LOG_LEVELS:
            raise ValueError(
                f"Unsupported logging level '{value}'. Valid levels: {sorted(_VALID_LOG_LEVELS)}"
            )
        return level

    @field_validator("theme")
    @classmethod
    def _validate_theme(cls, value: str) -> str:
        theme = value.lower().strip()
        if theme not in _VALID_THEMES:
            raise ValueError(
                f"Unsupported theme '{value}'. Valid themes: {sorted(_VALID_THEMES)}"
            )
        return theme


class DesktopConfigManager:
    """Manage the desktop configuration lifecycle with validation and migrations."""

    CURRENT_SCHEMA_VERSION = 1

    def __init__(self, app_name: str = APP_NAME, base_dir: Path | None = None) -> None:
        self.app_name = app_name
        self.base_dir = base_dir or self._resolve_app_dir(app_name)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.config_path = self.base_dir / CONFIG_FILENAME
        self.logs_dir = self.base_dir / "logs"
        self.logs_dir.mkdir(exist_ok=True)
        self.log_path = self.logs_dir / DEFAULT_LOG_NAME
        self.issue_dir = self.base_dir / "issues"
        self.issue_dir.mkdir(exist_ok=True)
        self.streamlit_dir = self.base_dir / STREAMLIT_DIRNAME
        self.streamlit_dir.mkdir(exist_ok=True)
        self.streamlit_config_path = self.streamlit_dir / STREAMLIT_CONFIG

    # ------------------------------------------------------------------
    # public helpers
    # ------------------------------------------------------------------
    def load(self) -> DesktopConfigModel:
        """Return the effective configuration, applying defaults as needed."""

        payload = self._default_payload()
        if self.config_path.exists():
            try:
                raw = yaml.safe_load(self.config_path.read_text(encoding="utf-8")) or {}
                if isinstance(raw, dict):
                    payload.update(raw)
            except Exception as exc:  # pragma: no cover - defensive read
                LOG.warning("Failed to read %s: %s", self.config_path, exc)
        payload.setdefault("schema_version", self.CURRENT_SCHEMA_VERSION)
        try:
            model = DesktopConfigModel.model_validate(payload)
        except ValidationError as exc:
            raise ValueError(f"Invalid desktop configuration: {exc}") from exc
        self._write_streamlit_theme(model.theme)
        return model

    def save(self, config: DesktopConfigModel) -> None:
        """Persist ``config`` to disk and apply shell side-effects."""

        data = self._redacted_dict(config, redact_secrets=False)
        data["schema_version"] = self.CURRENT_SCHEMA_VERSION
        yaml.safe_dump(data, self.config_path.open("w", encoding="utf-8"), sort_keys=True)
        self._write_streamlit_theme(config.theme)
        self.apply_environment(config)
        self._apply_autostart(config.autostart)

    def update(self, **changes: Any) -> DesktopConfigModel:
        """Apply ``changes`` and return the resulting model after validation."""

        config = self.load()
        payload = config.model_dump()
        payload.update(changes)
        try:
            model = DesktopConfigModel.model_validate(payload)
        except ValidationError as exc:
            raise ValueError(f"Invalid configuration update: {exc}") from exc
        errors = self.validate_external(model)
        if errors:
            raise ValueError("; ".join(errors))
        self.save(model)
        return model

    def validate_external(self, config: DesktopConfigModel) -> list[str]:
        """Perform IO-heavy validation checks (database, filesystem)."""

        errors: list[str] = []
        se_path = config.se_ephe_path.strip()
        if se_path and not Path(se_path).expanduser().exists():
            errors.append(f"Swiss ephemeris path does not exist: {se_path}")
        db_error = self._probe_database(config.database_url)
        if db_error:
            errors.append(db_error)
        return errors

    def probe_database(self, url: str) -> str | None:
        """Public entrypoint to validate a database URL."""

        return self._probe_database(url)

    def check_ephemeris_path(self, path: str) -> bool:
        """Return ``True`` if ``path`` exists or is left blank."""

        if not path:
            return True
        return Path(path).expanduser().exists()

    def apply_environment(self, config: DesktopConfigModel | None = None) -> None:
        """Set process environment variables for the active configuration."""

        config = config or self.load()
        os.environ["ASTROENGINE_HOME"] = str(self.base_dir)
        os.environ["DATABASE_URL"] = config.database_url
        os.environ["AE_QCACHE_SEC"] = str(config.qcache_sec)
        os.environ["AE_QCACHE_SIZE"] = str(config.qcache_size)
        os.environ["ASTROENGINE_LOG_LEVEL"] = config.logging_level
        if config.openai_api_key:
            os.environ["ASTROENGINE_OPENAI_KEY"] = config.openai_api_key
            os.environ["OPENAI_API_KEY"] = config.openai_api_key
        else:
            for key in ("ASTROENGINE_OPENAI_KEY", "OPENAI_API_KEY"):
                os.environ.pop(key, None)
        if config.openai_model:
            os.environ["ASTROENGINE_OPENAI_MODEL"] = config.openai_model
        if config.openai_base_url:
            os.environ["ASTROENGINE_OPENAI_BASE_URL"] = config.openai_base_url
        else:
            os.environ.pop("ASTROENGINE_OPENAI_BASE_URL", None)
        if config.se_ephe_path:
            os.environ["SE_EPHE_PATH"] = str(Path(config.se_ephe_path).expanduser())
        else:
            os.environ.pop("SE_EPHE_PATH", None)
        self._write_streamlit_theme(config.theme)
        self._apply_autostart(config.autostart)

    def redact(self, config: DesktopConfigModel | None = None) -> dict[str, Any]:
        """Return a JSON-serialisable dictionary with secrets removed."""

        config = config or self.load()
        return self._redacted_dict(config, redact_secrets=True)

    def ensure_issue_bundle(self, name: str, payload: dict[str, Any]) -> Path:
        """Persist ``payload`` as a JSON diagnostics artifact for support bundles."""

        safe_name = name.replace("/", "-").replace("\\", "-")
        target = self.issue_dir / f"{safe_name}.json"
        target.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return target

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _resolve_app_dir(app_name: str) -> Path:
        if platform.system() == "Windows":
            root = Path(os.environ.get("LOCALAPPDATA", Path.home()))
        else:
            root = Path(os.environ.get("ASTROENGINE_HOME", Path.home() / ".astroengine"))
        return Path(root) / app_name

    def _default_payload(self) -> dict[str, Any]:
        db_path = (self.base_dir / DEFAULT_DB_NAME).as_posix()
        return {
            "schema_version": self.CURRENT_SCHEMA_VERSION,
            "database_url": f"sqlite:///{db_path}",
            "se_ephe_path": "",
            "api_host": "127.0.0.1",
            "api_port": 8000,
            "streamlit_port": 8501,
            "qcache_sec": 1.0,
            "qcache_size": 4096,
            "logging_level": "INFO",
            "theme": "system",
            "openai_api_key": "",
            "openai_model": "gpt-4o-mini",
            "openai_base_url": None,
            "copilot_daily_limit": 50000,
            "copilot_session_limit": 8000,
            "autostart": False,
            "issue_report_dir": str(self.issue_dir),
        }

    def _probe_database(self, url: str) -> str | None:
        try:
            from sqlalchemy import create_engine, text

            engine = create_engine(url, pool_pre_ping=True)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception as exc:  # pragma: no cover - depends on drivers
            return f"Database connection failed: {exc}"
        return None

    def _redacted_dict(self, config: DesktopConfigModel, *, redact_secrets: bool) -> dict[str, Any]:
        data = config.model_dump()
        if redact_secrets:
            if data.get("openai_api_key"):
                data["openai_api_key"] = "*** configured ***"
        return data

    def _write_streamlit_theme(self, theme: str) -> None:
        if theme == "system":
            if self.streamlit_config_path.exists():
                try:
                    self.streamlit_config_path.unlink()
                except OSError:  # pragma: no cover - defensive cleanup
                    LOG.debug("Unable to remove %s", self.streamlit_config_path)
            return
        if theme == "high_contrast":
            config_text = (
                "[theme]\n"
                "base = \"dark\"\n"
                "primaryColor = \"#ffd166\"\n"
                "backgroundColor = \"#000000\"\n"
                "secondaryBackgroundColor = \"#161616\"\n"
                "textColor = \"#ffffff\"\n"
            )
        else:
            theme_value = "dark" if theme == "dark" else "light"
            config_text = "[theme]\nbase = \"{value}\"\n".format(value=theme_value)
        self.streamlit_config_path.write_text(config_text, encoding="utf-8")

    def _apply_autostart(self, enabled: bool) -> None:
        if platform.system() != "Windows":  # pragma: no cover - requires Windows
            return
        try:
            import winreg  # type: ignore[attr-defined]
        except Exception:  # pragma: no cover - module missing on non-Windows
            return
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
                if enabled:
                    command = self._autostart_command()
                    winreg.SetValueEx(key, self.app_name, 0, winreg.REG_SZ, command)
                else:
                    try:
                        winreg.DeleteValue(key, self.app_name)
                    except FileNotFoundError:
                        pass
        except OSError as exc:  # pragma: no cover - depends on permissions
            LOG.warning("Unable to update autostart flag: %s", exc)

    def _autostart_command(self) -> str:
        executable = Path(getattr(sys, "frozen", False) and sys.executable or sys.executable)
        if getattr(sys, "frozen", False):
            return str(executable)
        project_root = Path(__file__).resolve().parents[3]
        module_path = project_root / "app" / "desktop" / "launch_desktop.py"
        return f'"{sys.executable}" "{module_path}"'


__all__ = ["DesktopConfigManager", "DesktopConfigModel"]
