"""Configuration models and helpers for AstroEngine settings."""

from __future__ import annotations

import os
from copy import deepcopy
from pathlib import Path
from typing import Dict, List, Literal, Optional, Tuple

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

from astroengine.plugins.registry import apply_plugin_settings


CURRENT_SETTINGS_SCHEMA_VERSION = 2

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
    topocentric: bool = False
    house_offset_deg: float = 0.0
    zero_based_numbering: bool = False

    @field_validator("house_offset_deg", mode="before")
    @classmethod
    def _cap_house_offset(cls, value: float) -> float:
        numeric = float(value)
        return max(0.0, min(2.0, numeric))


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
    weights_by_aspect: Dict[str, int] = Field(
        default_factory=lambda: {
            "conjunction": 5,
            "opposition": 4,
            "trine": 3,
            "square": 3,
            "sextile": 2,
            "quincunx": 1,
            "semisextile": 1,
            "sesquisquare": 1,
            "quintile": 1,
            "biquintile": 1,
        }
    )
    applying_bonus_deg: float = 0.5
    separating_penalty_deg: float = 0.5
    orb_scaling: Literal["none", "luminary_priority", "magnitude"] = "luminary_priority"
    harmonics_n: int = 5
    pattern_tolerance_deg: float = 2.0
    use_moiety: bool = True
    show_applying: bool = True

    @field_validator("orbs_by_body", mode="before")
    @classmethod
    def _cap_orbs_by_body(cls, data: Dict[str, float] | object) -> Dict[str, float] | object:
        if not isinstance(data, dict):
            return data
        return {
            key: max(0.0, min(15.0, float(value)))
            for key, value in data.items()
        }

    @field_validator("weights_by_aspect", mode="before")
    @classmethod
    def _cap_aspect_weights(
        cls, data: Dict[str, int] | object
    ) -> Dict[str, int] | object:
        if not isinstance(data, dict):
            return data

        def _cap(value: int) -> int:
            return max(-10, min(10, int(value)))

        return {key: _cap(value) for key, value in data.items()}

    @field_validator("applying_bonus_deg", "separating_penalty_deg", mode="before")
    @classmethod
    def _cap_bias(cls, value: float) -> float:
        numeric = float(value)
        return max(0.0, min(3.0, numeric))

    @field_validator("harmonics_n", mode="before")
    @classmethod
    def _cap_harmonics(cls, value: int) -> int:
        return max(1, min(32, int(value)))

    @field_validator("pattern_tolerance_deg", mode="before")
    @classmethod
    def _cap_pattern_tolerance(cls, value: float) -> float:
        numeric = float(value)
        return max(0.5, min(5.0, numeric))


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


class NarrativeEsotericCfg(BaseModel):
    """Optional esoteric add-ons that influence narrative tone."""

    tarot_enabled: bool = False
    tarot_deck: str = "rws"
    numerology_enabled: bool = False
    numerology_system: str = "pythagorean"


class NarrativeCfg(BaseModel):
    """Narrative rendering preferences for interpretive output."""

    mode: str = "modern_psychological"
    library: Literal["western_basic", "hellenistic", "vedic", "none"] = "western_basic"
    tone: Literal["neutral", "teaching", "brief"] = "neutral"
    length: Literal["short", "medium", "long"] = "medium"
    language: str = "en"
    disclaimers: bool = True
    verbosity: float = 0.5
    sources: Dict[str, bool] = Field(default_factory=dict)
    frameworks: Dict[str, bool] = Field(default_factory=dict)
    esoteric: NarrativeEsotericCfg = Field(default_factory=NarrativeEsotericCfg)

    @field_validator("verbosity", mode="before")
    @classmethod
    def _cap_verbosity(cls, value: float) -> float:
        numeric = float(value)
        return max(0.0, min(1.0, numeric))


class NarrativeMixCfg(BaseModel):
    """Weighted blend of narrative profiles."""

    enabled: bool = False
    profiles: Dict[str, float] = Field(default_factory=dict)
    normalize: bool = True

    @field_validator("profiles", mode="before")
    @classmethod
    def _coerce_weights(cls, value: object) -> Dict[str, float]:
        if isinstance(value, dict):
            items = value.items()
        else:
            try:
                mapping = dict(value or {})  # type: ignore[arg-type]
            except Exception:
                return {}
            items = mapping.items()
        capped: Dict[str, float] = {}
        for key, weight in items:
            try:
                numeric = float(weight)
            except (TypeError, ValueError):
                continue
            if numeric < 0:
                numeric = 0.0
            capped[key] = min(numeric, 1_000_000.0)
        return capped

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
    line_thickness: float = 1.5
    grid_density: int = 5
    star_mag_limit: float = 6.0

    @field_validator("line_thickness", mode="before")
    @classmethod
    def _cap_line_thickness(cls, value: float) -> float:
        numeric = float(value)
        return max(0.5, min(5.0, numeric))

    @field_validator("grid_density", mode="before")
    @classmethod
    def _cap_grid_density(cls, value: int) -> int:
        return max(3, min(12, int(value)))

    @field_validator("star_mag_limit", mode="before")
    @classmethod
    def _cap_star_magnitude(cls, value: float) -> float:
        numeric = float(value)
        return max(-1.5, min(8.0, numeric))


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


class SwissCapsCfg(BaseModel):
    """Swiss Ephemeris capability boundaries."""

    min_year: int = 1800
    max_year: int = 2200


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
    workers: int = 1
    batch_size: int = 256

    @field_validator("workers", mode="before")
    @classmethod
    def _cap_workers(cls, value: int) -> int:
        return max(1, min(8, int(value)))

    @field_validator("batch_size", mode="before")
    @classmethod
    def _cap_batch_size(cls, value: int) -> int:
        return max(64, min(8192, int(value)))


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
    show_breakdown: bool = True
    normalize_to_scale: int = 100

    class Weights(BaseModel):
        domicile: int = 5
        exaltation: int = 4
        triplicity: int = 3
        term: int = 2
        face: int = 1
        detriment: int = -5
        fall: int = -4
        angular: int = 5
        succedent: int = 2
        cadent: int = -2
        retrograde: int = -5
        combustion: int = -5
        cazimi: int = 5
        under_beams: int = -2
        peregrine: int = -1

        @field_validator("*", mode="before")
        @classmethod
        def _cap_weights(cls, value: int) -> int:
            return max(-10, min(10, int(value)))

    weights: Weights = Field(default_factory=Weights)


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
    exactness_deg: float = 0.5
    consolidate_hours: int = 24
    min_orb_deg: float = 0.25

    @field_validator("exactness_deg", "min_orb_deg", mode="before")
    @classmethod
    def _cap_forecast_orbs(cls, value: float) -> float:
        numeric = float(value)
        return max(0.0, min(3.0, numeric))

    @field_validator("consolidate_hours", mode="before")
    @classmethod
    def _cap_consolidate_hours(cls, value: int) -> int:
        return max(1, min(168, int(value)))


class SynastryCfg(BaseModel):
    """Synastry depth controls."""

    declination: bool = False
    house_overlays: bool = True
    progressed_composite: bool = False


class ElectionalCfg(BaseModel):
    """Electional search constraints."""

    enabled: bool = False
    constraints: List[Dict[str, object]] = Field(default_factory=list)
    step_minutes: int = 5

    class Weights(BaseModel):
        benefic_on_angles: int = 5
        malefic_on_angles: int = -5
        moon_void: int = -7
        dignity_bonus: int = 3
        retrograde_penalty: int = -3
        combustion_penalty: int = -4
        cazimi_bonus: int = 4

        @field_validator("*", mode="before")
        @classmethod
        def _cap_weights(cls, value: int) -> int:
            return max(-10, min(10, int(value)))

    weights: Weights = Field(default_factory=Weights)

    @field_validator("step_minutes", mode="before")
    @classmethod
    def _cap_step_minutes(cls, value: int) -> int:
        return max(1, min(60, int(value)))


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
    online_fallback_enabled: bool = False


class ObservabilityCfg(BaseModel):
    """Observability and telemetry controls."""

    otel_enabled: bool = False
    sampling_ratio: float = 0.1
    metrics_histogram_buckets: List[float] = Field(
        default_factory=lambda: [0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0]
    )

    @field_validator("sampling_ratio", mode="before")
    @classmethod
    def _cap_sampling_ratio(cls, value: float) -> float:
        numeric = float(value)
        return max(0.0, min(1.0, numeric))


class ChatCfg(BaseModel):
    """In-app chat assistant configuration."""

    enabled: bool = True
    model: str = "gpt-4o-mini"
    temperature: float = 0.4
    max_tokens: int = 1000
    token_budget_session: int = 200000
    tools_enabled: bool = True

    @field_validator("temperature", mode="before")
    @classmethod
    def _cap_temperature(cls, value: float) -> float:
        numeric = float(value)
        return max(0.0, min(2.0, numeric))

    @field_validator("max_tokens", "token_budget_session", mode="before")
    @classmethod
    def _cap_token_counts(cls, value: int) -> int:
        return max(1, min(1_000_000, int(value)))


class Settings(BaseModel):
    """Top-level settings model persisted on disk."""

    schema_version: int = Field(
        default=CURRENT_SETTINGS_SCHEMA_VERSION,
        ge=1,
        description="Version marker for persisted configuration payloads.",
    )
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
    swiss_caps: SwissCapsCfg = Field(default_factory=SwissCapsCfg)
    perf: PerfCfg = Field(default_factory=PerfCfg)
    observability: ObservabilityCfg = Field(default_factory=ObservabilityCfg)
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
    narrative_mix: NarrativeMixCfg = Field(default_factory=NarrativeMixCfg)


# -------------------- Narrative Mixing Helpers --------------------


def _normalize_weights(weights: Dict[str, float]) -> Dict[str, float]:
    total = sum(weights.values())
    if total <= 0:
        return {name: 0.0 for name in weights}
    return {name: (value / total) for name, value in weights.items()}


_TONE_ORDER: Tuple[str, ...] = ("brief", "neutral", "teaching")
_LENGTH_ORDER: Tuple[str, ...] = ("short", "medium", "long")


def _vote_enum(values: List[str], weights: List[float], order: Tuple[str, ...]) -> str:
    if not order:
        return ""
    scores = {choice: 0.0 for choice in order}
    for value, weight in zip(values, weights):
        if value in scores:
            scores[value] += weight
    return max(scores.items(), key=lambda item: item[1])[0]


def _merge_bool_maps(
    maps: List[Dict[str, bool]],
    weights: List[float],
    *,
    threshold: float = 0.5,
) -> Dict[str, bool]:
    keys = set()
    for mapping in maps:
        keys.update(mapping.keys())
    result: Dict[str, bool] = {}
    for key in sorted(keys):
        score = 0.0
        for mapping, weight in zip(maps, weights):
            if mapping.get(key, False):
                score += weight
        result[key] = score >= threshold
    return result


def compose_narrative_from_mix(base: Settings, mix: NarrativeMixCfg) -> NarrativeCfg:
    """Blend narrative overlays declared in ``mix`` onto ``base``."""

    if not mix.enabled or not mix.profiles:
        return base.narrative

    positive = {name: float(weight) for name, weight in mix.profiles.items() if weight > 0}
    if not positive:
        return base.narrative

    from .narrative_profiles import load_narrative_profile_overlay

    entries: List[Tuple[str, float, NarrativeCfg]] = []
    for name, weight in positive.items():
        try:
            overlay = load_narrative_profile_overlay(name)
        except FileNotFoundError:
            continue
        block = overlay.get("narrative") or overlay
        try:
            merged = {**base.narrative.model_dump(), **block}
            cfg = NarrativeCfg(**merged)
        except Exception:
            continue
        entries.append((name, weight, cfg))

    if not entries:
        return base.narrative

    names = [name for name, _, _ in entries]
    weights = [weight for _, weight, _ in entries]
    if mix.normalize:
        normalized = _normalize_weights(dict(zip(names, weights)))
        weights = [normalized[name] for name in names]

    narratives = [cfg for _, _, cfg in entries]
    top_index = max(range(len(weights)), key=lambda idx: weights[idx])
    top_narrative = narratives[top_index]

    tones = [cfg.tone for cfg in narratives]
    lengths = [cfg.length for cfg in narratives]
    verb = sum((cfg.verbosity or 0.0) * weight for cfg, weight in zip(narratives, weights))

    sources = _merge_bool_maps([cfg.sources for cfg in narratives], weights)
    frameworks = _merge_bool_maps([cfg.frameworks for cfg in narratives], weights)

    tarot_enabled_score = sum(
        (1.0 if cfg.esoteric.tarot_enabled else 0.0) * weight
        for cfg, weight in zip(narratives, weights)
    )
    numerology_enabled_score = sum(
        (1.0 if cfg.esoteric.numerology_enabled else 0.0) * weight
        for cfg, weight in zip(narratives, weights)
    )

    sorted_entries = sorted(
        zip(narratives, weights), key=lambda item: item[1], reverse=True
    )
    tarot_deck = base.narrative.esoteric.tarot_deck
    numerology_system = base.narrative.esoteric.numerology_system
    for cfg, weight in sorted_entries:
        if cfg.esoteric.tarot_enabled:
            tarot_deck = cfg.esoteric.tarot_deck
            break
    for cfg, weight in sorted_entries:
        if cfg.esoteric.numerology_enabled:
            numerology_system = cfg.esoteric.numerology_system
            break

    payload = base.narrative.model_dump()
    payload.update(
        {
            "mode": "mixed",
            "library": top_narrative.library,
            "tone": _vote_enum(tones, weights, _TONE_ORDER),
            "length": _vote_enum(lengths, weights, _LENGTH_ORDER),
            "verbosity": max(0.0, min(1.0, verb)),
            "sources": sources,
            "frameworks": frameworks,
            "esoteric": {
                "tarot_enabled": tarot_enabled_score >= 0.5,
                "tarot_deck": tarot_deck,
                "numerology_enabled": numerology_enabled_score >= 0.5,
                "numerology_system": numerology_system,
            },
            "disclaimers": bool(
                base.narrative.disclaimers
                or any(cfg.disclaimers for cfg in narratives)
            ),
        }
    )
    return NarrativeCfg(**payload)


def save_mix_as_user_narrative_profile(
    name: str, base: Settings, mix: NarrativeMixCfg
) -> Path:
    from .narrative_profiles import save_user_narrative_profile

    narrative = compose_narrative_from_mix(base, mix)
    return save_user_narrative_profile(name, narrative)



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


def _coerce_schema_version(raw: object) -> int:
    """Return a normalised schema version value with sane bounds."""

    try:
        value = int(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 1
    return max(1, value)


def _upgrade_settings_payload(
    data: dict[str, object], *, schema_version: int
) -> tuple[dict[str, object], bool]:
    """Apply in-place upgrades required for older settings payloads."""

    upgraded = deepcopy(data)
    version = max(1, schema_version)
    changed = False

    if version < 2:
        # v2 introduces the explicit schema version marker. No structural
        # adjustments are required; we simply record the new version.
        version = 2
        changed = True

    if version < CURRENT_SETTINGS_SCHEMA_VERSION:
        version = CURRENT_SETTINGS_SCHEMA_VERSION
        changed = True

    if upgraded.get("schema_version") != version:
        upgraded["schema_version"] = version
        changed = True

    return upgraded, changed


def load_settings(path: Optional[Path] = None) -> Settings:
    """Load settings from disk, creating defaults if missing."""

    source_path = Path(path) if path else config_path()
    if not source_path.exists():
        settings = default_settings()
        save_settings(settings, source_path)
        return settings
    with source_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    if not isinstance(raw, dict):
        raw = {}
    schema_version = _coerce_schema_version(raw.get("schema_version"))
    data, upgraded = _upgrade_settings_payload(raw, schema_version=schema_version)
    settings = Settings(**data)
    if upgraded:
        save_settings(settings, source_path)
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

