"""Runtime configuration loaded from environment variables and .env files."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import AnyUrl, Field, PrivateAttr, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

if TYPE_CHECKING:  # pragma: no cover - imported for type checking only
    from astroengine.config.settings import Settings as PersistedSettings


def _default_home() -> Path:
    """Return the default AstroEngine home directory."""

    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "AstroEngine"
    return Path.home() / ".astroengine"


_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class RuntimeSettings(BaseSettings):
    """Runtime configuration resolved from the process environment."""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_nested_delimiter="__",
        extra="ignore",
    )

    environment: str = Field(default="dev", alias="ENV")
    astroengine_home: Path = Field(default_factory=_default_home, alias="ASTROENGINE_HOME")
    database_url: str = Field(default="sqlite:///./dev.db", alias="DATABASE_URL")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    se_ephe_path: Path | None = Field(default=None, alias="SE_EPHE_PATH")
    swe_eph_path: Path | None = Field(default=None, alias="SWE_EPH_PATH")
    safe_mode: bool = Field(default=False, alias="SAFE_MODE")
    dev_mode: bool = Field(default=False, alias="DEV_MODE")
    trust_proxy: bool = Field(default=False, alias="TRUST_PROXY")
    openai_api_key: SecretStr | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str | None = Field(default=None, alias="OPENAI_MODEL")
    openai_base_url: AnyUrl | None = Field(default=None, alias="OPENAI_BASE_URL")
    reload_persisted_on_access: bool = Field(default=False, alias="ASTROENGINE_RELOAD_SETTINGS")
    settings_file: Path | None = Field(default=None, alias="ASTROENGINE_SETTINGS_FILE")
    plugin_autoload: bool = Field(default=True, alias="ASTROENGINE_ENABLE_PLUGINS")

    _persisted_cache: PersistedSettings | None = PrivateAttr(default=None)

    @field_validator("astroengine_home", mode="before")
    @classmethod
    def _validate_home(cls, value: Path | str | None) -> Path:
        if value is None or value == "":
            return _default_home()
        return Path(value).expanduser()

    @field_validator("se_ephe_path", "swe_eph_path", "settings_file", mode="before")
    @classmethod
    def _expand_optional_path(
        cls, value: Path | str | None
    ) -> Path | None:
        if value in {None, ""}:
            return None
        return Path(value).expanduser()

    @model_validator(mode="after")
    def _propagate_ephemeris_alias(self) -> "RuntimeSettings":
        if self.se_ephe_path is None and self.swe_eph_path is not None:
            object.__setattr__(self, "se_ephe_path", self.swe_eph_path)
        return self

    def config_file_path(self) -> Path:
        """Return the effective path to the persisted settings file."""

        if self.settings_file is not None:
            return self.settings_file
        from astroengine.config.settings import config_path

        return config_path()

    def persisted(
        self, *, fresh: bool = False
    ) -> "PersistedSettings":
        """Return a deep copy of the persisted settings, loading from disk once."""

        from astroengine.config.settings import load_settings

        if fresh or self.reload_persisted_on_access or self._persisted_cache is None:
            path = self.settings_file
            self._persisted_cache = load_settings(path)
        return self._persisted_cache.model_copy(deep=True)

    def cache_persisted(self, payload: "PersistedSettings") -> None:
        """Update the in-memory cache of persisted settings."""

        self._persisted_cache = payload.model_copy(deep=True)

    def clear_persisted_cache(self) -> None:
        """Clear any cached persisted settings forcing a reload on next access."""

        self._persisted_cache = None

    @property
    def ephemeris_path(self) -> Path | None:
        """Return the configured Swiss Ephemeris path, if provided."""

        return self.se_ephe_path


runtime_settings = RuntimeSettings()

# Backwards compatibility aliases
Settings = RuntimeSettings
settings = runtime_settings

__all__ = ["RuntimeSettings", "runtime_settings", "Settings", "settings"]

