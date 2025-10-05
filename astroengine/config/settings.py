"""Configuration models and helpers for AstroEngine settings."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Literal, Optional

import yaml
from pydantic import BaseModel, Field

# -------------------- Settings Schema --------------------


class ZodiacCfg(BaseModel):
    """Zodiac configuration for chart calculations."""

    type: Literal["tropical", "sidereal"] = "tropical"
    ayanamsa: Literal[
        "lahiri",
        "fagan_bradley",
        "krishnamurti",
        "de_luce",
        "raman",
        "none",
    ] = "lahiri"


class HousesCfg(BaseModel):
    """House system configuration."""

    system: Literal[
        "placidus",
        "whole_sign",
        "equal",
        "koch",
        "porphyry",
        "regiomontanus",
        "alcabitius",
        "campanus",
    ] = "placidus"


class BodiesCfg(BaseModel):
    """Configuration for body groups and custom asteroid selections."""

    groups: Dict[str, bool] = Field(
        default_factory=lambda: {
            "luminaries": True,
            "classical": True,
            "modern": True,
            "dwarf": False,
            "centaurs": False,
            "asteroids_major": False,
            "asteroids_extended": False,
            "hypothetical": False,
        }
    )
    custom_asteroids: List[int] = Field(default_factory=list)


class AspectsCfg(BaseModel):
    """Aspect detection and orb configuration."""

    sets: Dict[str, bool] = Field(
        default_factory=lambda: {
            "ptolemaic": True,
            "minor": True,
            "harmonics": False,
        }
    )
    detect_patterns: bool = True
    orbs_global: float = 6.0
    orbs_by_aspect: Dict[str, float] = Field(
        default_factory=lambda: {
            "conjunction": 8.0,
            "opposition": 8.0,
            "trine": 7.0,
            "square": 6.0,
            "sextile": 4.0,
        }
    )
    orbs_by_body: Dict[str, float] = Field(
        default_factory=lambda: {
            "sun": 10.0,
            "moon": 8.0,
        }
    )
    use_moiety: bool = True
    show_applying: bool = True


class ChartsCfg(BaseModel):
    """Toggle availability of chart techniques exposed by the engine."""

    enabled: Dict[str, bool] = Field(
        default_factory=lambda: {
            "natal": True,
            "transit_moment": True,
            "transit_to_natal": True,
            "synastry": True,
            "composite": True,
            "davison": True,
            "solar_return": True,
            "lunar_return": True,
            "secondary_progressions": True,
            "solar_arc": True,
            "annual_profections": True,
            "zodiacal_releasing": False,
            "firdaria": False,
            "primary_directions": False,
            "vedic_dasha_vimshottari": False,
            "vedic_dasha_yogini": False,
            "varga_d1": True,
            "varga_d9": False,
            "varga_d10": False,
        }
    )


class NarrativeCfg(BaseModel):
    """Narrative rendering preferences for interpretive output."""

    library: Literal["western_basic", "hellenistic", "vedic", "none"] = "western_basic"
    tone: Literal["neutral", "teaching", "brief"] = "neutral"
    length: Literal["short", "medium", "long"] = "medium"
    language: str = "en"
    disclaimers: bool = True


class RenderingCfg(BaseModel):
    """Chart rendering options."""

    layers: Dict[str, bool] = Field(
        default_factory=lambda: {
            "wheel": True,
            "aspect_lines": True,
            "grid": True,
            "patterns": True,
            "dignities": False,
            "retro_markers": True,
        }
    )
    theme: Literal["dark", "light", "high_contrast"] = "dark"
    glyph_set: Literal["default", "classic", "modern"] = "default"


class EphemerisCfg(BaseModel):
    """Ephemeris source configuration."""

    source: Literal["swiss", "approx"] = "swiss"
    path: Optional[str] = None
    precision: Literal["normal", "high"] = "normal"


class PerfCfg(BaseModel):
    """Performance tuning options for heavy calculations."""

    qcache_size: int = 4096
    qcache_sec: float = 1.0
    max_scan_days: int = 365


class AtlasCfg(BaseModel):
    """Atlas and geocoding configuration."""

    offline_enabled: bool = False
    data_path: Optional[str] = None


class Settings(BaseModel):
    """Top-level settings model persisted on disk."""

    preset: Literal[
        "modern_western",
        "traditional_western",
        "hellenistic",
        "vedic",
        "minimalist",
    ] = "modern_western"
    zodiac: ZodiacCfg = Field(default_factory=ZodiacCfg)
    houses: HousesCfg = Field(default_factory=HousesCfg)
    bodies: BodiesCfg = Field(default_factory=BodiesCfg)
    aspects: AspectsCfg = Field(default_factory=AspectsCfg)
    charts: ChartsCfg = Field(default_factory=ChartsCfg)
    narrative: NarrativeCfg = Field(default_factory=NarrativeCfg)
    rendering: RenderingCfg = Field(default_factory=RenderingCfg)
    ephemeris: EphemerisCfg = Field(default_factory=EphemerisCfg)
    perf: PerfCfg = Field(default_factory=PerfCfg)
    atlas: AtlasCfg = Field(default_factory=AtlasCfg)


# -------------------- I/O Helpers --------------------

CONFIG_FILENAME = "config.yaml"


def get_config_home() -> Path:
    """Return the directory where settings should be stored."""

    if os.name == "nt":
        base = Path(
            os.environ.get(
                "LOCALAPPDATA", str(Path.home() / "AppData" / "Local")
            )
        )
        return base / "AstroEngine"
    return Path(os.environ.get("ASTROENGINE_HOME", str(Path.home() / ".astroengine")))


def config_path() -> Path:
    """Return the full path to the configuration file, creating directories as needed."""

    home = get_config_home()
    home.mkdir(parents=True, exist_ok=True)
    return home / CONFIG_FILENAME


def default_settings() -> Settings:
    """Instantiate a Settings object populated with defaults."""

    return Settings()


def save_settings(settings: Settings, path: Optional[Path] = None) -> Path:
    """Persist the given settings to disk as YAML."""

    target_path = Path(path) if path else config_path()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    data = settings.model_dump()
    with target_path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=False, allow_unicode=True)
    return target_path


def load_settings(path: Optional[Path] = None) -> Settings:
    """Load settings from disk, creating defaults if missing."""

    source_path = Path(path) if path else config_path()
    if not source_path.exists():
        settings = default_settings()
        save_settings(settings, source_path)
        return settings
    with source_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return Settings(**data)


def ensure_default_config() -> Path:
    """Ensure a configuration file exists on disk and return its path."""

    target = config_path()
    if not target.exists():
        save_settings(default_settings(), target)
    return target

