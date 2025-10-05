"""Configuration models and helpers for AstroEngine settings."""

from __future__ import annotations

import os
from copy import deepcopy
from pathlib import Path
from typing import Dict, List, Literal, Optional

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

from astroengine.plugins.registry import apply_plugin_settings

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


class AntisciaCfg(BaseModel):
    """Configuration for antiscia/contra-antiscia mirror detection."""

    enabled: bool = False
    orb: float = 2.0
    show_overlay: bool = False


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
    verbosity: float = 0.5
    mode: Literal[
        "data_minimal",
        "traditional_classical",
        "modern_psychological",
        "vedic_parashari",
        "jungian_archetypal",
        "esoteric_tarot",
        "esoteric_numerology",
        "esoteric_mixed",
    ] = "modern_psychological"
    sources: Dict[str, bool] = Field(
        default_factory=lambda: {
            "aspects": True,
            "dignities": True,
            "sect": True,
            "lots": True,
            "fixed_stars": False,
            "declinations": False,
            "antiscia": False,
            "midpoints": True,
        }
    )
    frameworks: Dict[str, bool] = Field(
        default_factory=lambda: {
            "jungian": False,
            "mythic": False,
            "hellenistic": False,
            "vedic": False,
            "psychological": True,
            "medical": False,
        }
    )
    esoteric: Dict[str, bool | str] = Field(
        default_factory=lambda: {
            "tarot_enabled": False,
            "tarot_deck": "rws",
            "numerology_enabled": False,
            "numerology_system": "pythagorean",
        }
    )

    @field_validator("verbosity", mode="before")
    @classmethod
    def _cap_verbosity(cls, value: float) -> float:
        value = float(value)
        return max(0.0, min(1.0, value))


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


class FixedStarsCfg(BaseModel):
    """Fixed star visibility and orb defaults."""

    enabled: bool = False
    orb_deg: float = 1.0
    catalog: str = "robson"


class EphemerisCfg(BaseModel):
    """Ephemeris source configuration."""

    source: Literal["swiss", "approx"] = "swiss"
    path: Optional[str] = None
    precision: Literal["normal", "high"] = "normal"


class ReturnsIngressCfg(BaseModel):
    """Feature toggles for return charts and ingress lookups."""

    solar_return: bool = True
    lunar_return: bool = True
    aries_ingress: bool = True
    lunar_count: int = Field(12, ge=1, le=36)
    timezone: Optional[str] = None


class PerfCfg(BaseModel):
    """Performance tuning options for heavy calculations."""

    qcache_size: int = 4096
    qcache_sec: float = 1.0
    max_scan_days: int = 365


class AstroCartoCfg(BaseModel):
    """Astrocartography rendering controls."""

    enabled: bool = False
    show_parans: bool = False


class AstrocartographyCfg(AstroCartoCfg):
    """Backward-compatible alias for :class:`AstroCartoCfg`."""


class MidpointTreeCfg(BaseModel):
    """Tree settings for midpoint expansion."""

    enabled: bool = False
    max_depth: int = 2


class MidpointsCfg(BaseModel):
    """Midpoint feature toggles."""

    enabled: bool = True
    tree: MidpointTreeCfg = Field(default_factory=MidpointTreeCfg)


class FixedStarsCfg(BaseModel):
    """Configuration for fixed star inclusion."""

    enabled: bool = False
    catalog: Literal["robson", "brady"] = "robson"
    orb_deg: float = 1.0


class AntisciaCfg(BaseModel):
    """Antiscia and contra-antiscia toggles."""

    enabled: bool = False
    include_contra: bool = True


class DignitiesCfg(BaseModel):
    """Dignity scoring options."""

    enabled: bool = True
    scoring: Literal["lilly", "ptolemy", "custom"] = "lilly"


class ArabicPartCustomCfg(BaseModel):
    """Custom arabic part formula definition."""

    name: str
    day_formula: str
    night_formula: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _alias_legacy_fields(cls, values: Dict[str, object]):
        """Accept legacy ``day``/``night`` keys alongside the new field names."""

        if isinstance(values, dict):
            if "day_formula" not in values and "day" in values:
                values = dict(values)
                values["day_formula"] = values.pop("day")
            if "night_formula" not in values and "night" in values:
                values = dict(values)
                values["night_formula"] = values.pop("night")
        return values

    @property
    def day(self) -> str:
        return self.day_formula

    @property
    def night(self) -> str | None:
        return self.night_formula


# Backwards compatibility alias – older code imported ``ArabicPartCustom``.
ArabicPartCustom = ArabicPartCustomCfg


class ArabicPartsCfg(BaseModel):
    """Arabic parts presets and custom definitions."""

    enabled: bool = True
    presets: Dict[str, bool] = Field(
        default_factory=lambda: {"Fortune": True, "Spirit": True}
    )
    custom: List[ArabicPartCustomCfg] = Field(default_factory=list)


class DeclinationAspectsCfg(BaseModel):
    """Declination aspect toggles."""

    parallel: bool = True
    contraparallel: bool = True


class DeclinationsCfg(BaseModel):
    """Declination analysis toggles."""

    enabled: bool = False
    aspects: DeclinationAspectsCfg = Field(default_factory=DeclinationAspectsCfg)
    orb_deg: float = 0.5


class EclipseFinderCfg(BaseModel):
    """Eclipse and lunation search configuration."""

    enabled: bool = False
    orb_days: int = 3


class VoidOfCourseCfg(BaseModel):
    """Void of course detection toggle."""

    enabled: bool = False


class StationsCfg(BaseModel):
    """Planetary station discovery configuration."""

    enabled: bool = True
    void_of_course: VoidOfCourseCfg = Field(default_factory=VoidOfCourseCfg)


class PrimaryDirectionsCfg(BaseModel):
    """Primary directions configuration."""

    enabled: bool = False
    key: Literal["placidean", "regiomontanus"] = "placidean"
    zodiacal: bool = False


class MultiWheelCfg(BaseModel):
    """Multiwheel rendering controls."""

    enabled: bool = True
    max_wheels: int = 3


class ForecastStackCfg(BaseModel):
    """Forecast stack component toggles."""

    enabled: bool = True
    components: List[str] = Field(
        default_factory=lambda: [
            "transits",
            "secondary_progressions",
            "solar_arc",
        ]
    )


class SynastryCfg(BaseModel):
    """Synastry depth controls."""

    declination: bool = False
    house_overlays: bool = True
    progressed_composite: bool = False


class ElectionalCfg(BaseModel):
    """Electional search constraints."""

    enabled: bool = False
    constraints: List[Dict[str, object]] = Field(default_factory=list)


class PluginCfg(BaseModel):
    """Plugin enablement state segregated by capability."""

    aspects: Optional[Dict[str, bool]] = None
    lots: Optional[Dict[str, bool]] = None


class ReturnsIngressCfg(BaseModel):
    """Return and ingress toggles."""

    solar_return: bool = True
    lunar_return: bool = True
    aries_ingress: bool = False


class TimelineUICfg(BaseModel):
    """Timeline UI behaviour toggles."""

    show_exact_only: bool = False
    max_events: int = 2000


class ReportsCfg(BaseModel):
    """Report generation preferences."""

    pdf_enabled: bool = False
    template: Literal["classic", "minimal"] = "classic"


class AtlasCfg(BaseModel):
    """Atlas availability configuration."""

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
    declinations: DeclinationsCfg = Field(default_factory=DeclinationsCfg)
    charts: ChartsCfg = Field(default_factory=ChartsCfg)
    narrative: NarrativeCfg = Field(default_factory=NarrativeCfg)
    rendering: RenderingCfg = Field(default_factory=RenderingCfg)
    fixed_stars: FixedStarsCfg = Field(default_factory=FixedStarsCfg)
    ephemeris: EphemerisCfg = Field(default_factory=EphemerisCfg)
    perf: PerfCfg = Field(default_factory=PerfCfg)
    astrocartography: AstroCartoCfg = Field(default_factory=AstroCartoCfg)
    midpoints: MidpointsCfg = Field(default_factory=MidpointsCfg)
    fixed_stars: FixedStarsCfg = Field(default_factory=FixedStarsCfg)
    antiscia: AntisciaCfg = Field(default_factory=AntisciaCfg)
    dignities: DignitiesCfg = Field(default_factory=DignitiesCfg)
    arabic_parts: ArabicPartsCfg = Field(default_factory=ArabicPartsCfg)
    declinations: DeclinationsCfg = Field(default_factory=DeclinationsCfg)
    eclipse_finder: EclipseFinderCfg = Field(default_factory=EclipseFinderCfg)
    stations: StationsCfg = Field(default_factory=StationsCfg)
    primary_directions: PrimaryDirectionsCfg = Field(
        default_factory=PrimaryDirectionsCfg
    )
    multiwheel: MultiWheelCfg = Field(default_factory=MultiWheelCfg)
    forecast_stack: ForecastStackCfg = Field(default_factory=ForecastStackCfg)
    synastry: SynastryCfg = Field(default_factory=SynastryCfg)
    electional: ElectionalCfg = Field(default_factory=ElectionalCfg)
    returns_ingress: ReturnsIngressCfg = Field(default_factory=ReturnsIngressCfg)
    timeline_ui: TimelineUICfg = Field(default_factory=TimelineUICfg)
    reports: ReportsCfg = Field(default_factory=ReportsCfg)
    atlas: AtlasCfg = Field(default_factory=AtlasCfg)
    plugins: PluginCfg = Field(default_factory=PluginCfg)


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
    apply_plugin_settings(settings)
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
    settings = Settings(**data)
    apply_plugin_settings(settings)
    return settings


def ensure_default_config() -> Path:
    """Ensure a configuration file exists on disk and return its path."""

    target = config_path()
    if not target.exists():
        save_settings(default_settings(), target)
    return target


# -------------------- Narrative profile overlays --------------------

NARRATIVE_PROFILES_SUBDIR = "profiles/narrative"


def narrative_profiles_home() -> Path:
    """Return the directory where narrative profile overlays are stored."""

    return get_config_home() / NARRATIVE_PROFILES_SUBDIR


def built_in_narrative_profiles() -> dict[str, dict]:
    """Return built-in narrative overlay definitions."""

    return {
        "data_minimal": {
            "narrative": {
                "mode": "data_minimal",
                "library": "none",
                "tone": "brief",
                "length": "short",
                "verbosity": 0.2,
                "sources": {
                    "aspects": True,
                    "dignities": False,
                    "sect": False,
                    "lots": False,
                    "fixed_stars": False,
                    "declinations": False,
                    "antiscia": False,
                    "midpoints": True,
                },
                "frameworks": {
                    "psychological": False,
                    "jungian": False,
                    "hellenistic": False,
                    "vedic": False,
                },
                "disclaimers": True,
            }
        },
        "traditional_classical": {
            "narrative": {
                "mode": "traditional_classical",
                "library": "hellenistic",
                "tone": "neutral",
                "length": "medium",
                "verbosity": 0.5,
                "sources": {
                    "aspects": True,
                    "dignities": True,
                    "sect": True,
                    "lots": True,
                    "fixed_stars": True,
                },
                "frameworks": {
                    "hellenistic": True,
                    "psychological": False,
                },
            }
        },
        "modern_psychological": {
            "narrative": {
                "mode": "modern_psychological",
                "library": "western_basic",
                "tone": "teaching",
                "length": "medium",
                "verbosity": 0.7,
                "sources": {
                    "aspects": True,
                    "midpoints": True,
                    "dignities": True,
                },
                "frameworks": {
                    "psychological": True,
                    "jungian": False,
                },
            }
        },
        "vedic_parashari": {
            "narrative": {
                "mode": "vedic_parashari",
                "library": "vedic",
                "tone": "neutral",
                "length": "medium",
                "verbosity": 0.6,
                "sources": {
                    "aspects": True,
                    "lots": False,
                    "dignities": True,
                },
                "frameworks": {
                    "vedic": True,
                },
            }
        },
        "jungian_archetypal": {
            "narrative": {
                "mode": "jungian_archetypal",
                "library": "western_basic",
                "tone": "teaching",
                "length": "long",
                "verbosity": 0.8,
                "sources": {
                    "aspects": True,
                    "midpoints": True,
                    "fixed_stars": False,
                },
                "frameworks": {
                    "psychological": True,
                    "jungian": True,
                },
            }
        },
        "esoteric_tarot": {
            "narrative": {
                "mode": "esoteric_tarot",
                "library": "western_basic",
                "tone": "brief",
                "length": "short",
                "verbosity": 0.5,
                "esoteric": {
                    "tarot_enabled": True,
                    "tarot_deck": "rws",
                    "numerology_enabled": False,
                },
            }
        },
        "esoteric_numerology": {
            "narrative": {
                "mode": "esoteric_numerology",
                "library": "western_basic",
                "tone": "brief",
                "length": "short",
                "verbosity": 0.5,
                "esoteric": {
                    "numerology_enabled": True,
                    "numerology_system": "pythagorean",
                    "tarot_enabled": False,
                },
            }
        },
        "esoteric_mixed": {
            "narrative": {
                "mode": "esoteric_mixed",
                "library": "western_basic",
                "tone": "teaching",
                "length": "medium",
                "verbosity": 0.7,
                "esoteric": {
                    "tarot_enabled": True,
                    "tarot_deck": "rws",
                    "numerology_enabled": True,
                    "numerology_system": "pythagorean",
                },
            }
        },
    }


def list_narrative_profiles() -> dict[str, list[str]]:
    """Return available narrative profile names segregated by origin."""

    built_in = sorted(built_in_narrative_profiles().keys())
    user: list[str] = []
    directory = narrative_profiles_home()
    if directory.exists():
        for path in directory.glob("*.yaml"):
            user.append(path.stem)
    return {"built_in": built_in, "user": sorted(user)}


def load_narrative_profile_overlay(name: str) -> dict:
    """Load a narrative profile overlay by name."""

    built_in = built_in_narrative_profiles()
    if name in built_in:
        return deepcopy(built_in[name])
    profile_path = narrative_profiles_home() / f"{name}.yaml"
    if not profile_path.exists():
        raise FileNotFoundError(name)
    return yaml.safe_load(profile_path.read_text(encoding="utf-8")) or {}


def apply_narrative_profile_overlay(base: Settings, overlay: dict) -> Settings:
    """Apply a narrative overlay to the provided settings model."""

    merged = base.model_dump()
    current_narrative = merged.get("narrative", {})
    overlay_narrative = overlay.get("narrative", {})
    combined = {**current_narrative, **overlay_narrative}
    for key in ("sources", "frameworks", "esoteric"):
        if isinstance(current_narrative.get(key), dict) and isinstance(
            overlay_narrative.get(key), dict
        ):
            combined[key] = {
                **current_narrative.get(key, {}),
                **overlay_narrative.get(key, {}),
            }
    merged["narrative"] = combined
    return Settings(**merged)


def save_user_narrative_profile(name: str, narrative: NarrativeCfg) -> Path:
    """Persist a user-defined narrative profile overlay to disk."""

    directory = narrative_profiles_home()
    directory.mkdir(parents=True, exist_ok=True)
    profile_path = directory / f"{name}.yaml"
    data = {"narrative": narrative.model_dump()}
    profile_path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return profile_path


def delete_user_narrative_profile(name: str) -> bool:
    """Delete a user-defined narrative profile if it exists."""

    profile_path = narrative_profiles_home() / f"{name}.yaml"
    if profile_path.exists():
        profile_path.unlink()
        return True
    return False

