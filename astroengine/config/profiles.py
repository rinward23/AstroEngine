"""Profiles registry and helpers for AstroEngine settings."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from .settings import Settings, get_config_home

PROFILES_DIRNAME = "profiles"

USE_CASE_PRESETS: tuple[str, ...] = (
    "horary_strict",
    "electional_strict",
    "counseling_modern",
    "minimalist",
)

PROFILE_LABELS: dict[str, str] = {
    "modern_western": "Modern Western (default)",
    "traditional_western": "Traditional Western",
    "hellenistic": "Hellenistic",
    "vedic": "Vedic",
    "horary": "Horary (legacy)",
    "horary_strict": "Horary — strict judgement",
    "electional": "Electional (legacy)",
    "electional_strict": "Electional — strict timing",
    "counseling_modern": "Counseling — modern psychological",
    "minimalist": "Minimalist essentials",
}

PROFILE_DESCRIPTIONS: dict[str, str] = {
    "horary_strict": (
        "Regiomontanus houses, classical planets only, and moiety-based orbs "
        "for traditional horary judgement."
    ),
    "electional_strict": (
        "Minute-by-minute scanning with strong benefic/void-of-course weights "
        "for rigorous electional filtering."
    ),
    "counseling_modern": (
        "Modern psychological framing with outer planets, minor aspects, and "
        "a teaching tone for client work."
    ),
    "minimalist": (
        "Luminaries and classical planets only with essential aspects for a "
        "focused chart read."
    ),
}


def profile_label(name: str) -> str:
    """Return a human-readable label for ``name``."""

    return PROFILE_LABELS.get(name, name.replace("_", " ").title())


def profile_description(name: str) -> str | None:
    """Return a short description for ``name`` if one is available."""

    return PROFILE_DESCRIPTIONS.get(name)


def built_in_profiles() -> dict[str, dict]:
    """Return overlays describing the built-in settings profiles."""

    return {
        "modern_western": {
            "preset": "modern_western",
            "zodiac": {"type": "tropical"},
            "houses": {"system": "placidus"},
            "aspects": {
                "sets": {"ptolemaic": True, "minor": True, "harmonics": False},
                "orbs_global": 6.0,
                "orbs_by_aspect": {
                    "conjunction": 8.0,
                    "opposition": 8.0,
                    "trine": 7.0,
                    "square": 6.0,
                    "sextile": 4.0,
                    "quincunx": 3.0,
                },
                "orbs_by_body": {"sun": 10.0, "moon": 8.0},
            },
            "narrative": {"library": "western_basic"},
        },
        "traditional_western": {
            "preset": "traditional_western",
            "zodiac": {"type": "tropical"},
            "houses": {"system": "regiomontanus"},
            "aspects": {
                "sets": {"ptolemaic": True, "minor": False, "harmonics": False},
                "orbs_by_aspect": {
                    "conjunction": 8.0,
                    "opposition": 8.0,
                    "trine": 6.0,
                    "square": 6.0,
                    "sextile": 4.0,
                },
            },
            "dignities": {
                "scoring": "lilly",
                "weights": {
                    "domicile": 5,
                    "exaltation": 4,
                    "triplicity": 3,
                    "term": 2,
                    "face": 1,
                    "detriment": -5,
                    "fall": -4,
                },
            },
        },
        "hellenistic": {
            "preset": "hellenistic",
            "houses": {"system": "whole_sign"},
            "aspects": {
                "sets": {"ptolemaic": True, "minor": False, "harmonics": False},
                "detect_patterns": False,
            },
            "narrative": {"library": "hellenistic"},
        },
        "vedic": {
            "preset": "vedic",
            "zodiac": {"type": "sidereal", "ayanamsa": "lahiri"},
            "houses": {"system": "whole_sign"},
            "aspects": {
                "sets": {"ptolemaic": False, "minor": False, "harmonics": False},
            },
            "charts": {
                "enabled": {
                    "varga_d1": True,
                    "varga_d9": True,
                    "varga_d10": True,
                    "vedic_dasha_vimshottari": True,
                    "vedic_dasha_yogini": True,
                }
            },
            "narrative": {"library": "vedic"},
        },
        "horary": {
            "preset": "traditional_western",
            "houses": {"system": "regiomontanus"},
            "aspects": {
                "sets": {"ptolemaic": True, "minor": False},
                "orbs_by_aspect": {
                    "conjunction": 5.0,
                    "opposition": 5.0,
                    "trine": 4.0,
                    "square": 4.0,
                    "sextile": 3.0,
                },
                "orbs_by_body": {"sun": 7.0, "moon": 6.0},
            },
            "declinations": {"orb_deg": 0.5},
            "dignities": {
                "weights": {"retrograde": -6, "combustion": -6, "cazimi": 6}
            },
        },
        "electional": {
            "preset": "modern_western",
            "electional": {
                "enabled": True,
                "weights": {
                    "benefic_on_angles": 6,
                    "malefic_on_angles": -6,
                    "moon_void": -8,
                    "dignity_bonus": 4,
                    "retrograde_penalty": -4,
                    "combustion_penalty": -5,
                    "cazimi_bonus": 5,
                },
                "step_minutes": 3,
            },
            "forecast_stack": {"exactness_deg": 0.25, "min_orb_deg": 0.25},
        },
        "electional_strict": {
            "preset": "modern_western",
            "bodies": {
                "groups": {
                    "luminaries": True,
                    "classical": True,
                    "modern": True,
                    "dwarf": False,
                    "centaurs": False,
                    "asteroids_major": False,
                }
            },
            "aspects": {
                "sets": {"ptolemaic": True, "minor": False, "harmonics": False},
                "detect_patterns": False,
                "orbs_global": 4.0,
                "orbs_by_aspect": {
                    "conjunction": 6.0,
                    "opposition": 6.0,
                    "trine": 5.0,
                    "square": 5.0,
                    "sextile": 3.5,
                },
                "orbs_by_body": {"sun": 9.0, "moon": 7.5},
            },
            "forecast_stack": {
                "exactness_deg": 0.2,
                "min_orb_deg": 0.2,
                "consolidate_hours": 6,
            },
            "electional": {
                "enabled": True,
                "step_minutes": 2,
                "weights": {
                    "benefic_on_angles": 7,
                    "malefic_on_angles": -7,
                    "moon_void": -9,
                    "dignity_bonus": 4,
                    "retrograde_penalty": -5,
                    "combustion_penalty": -5,
                    "cazimi_bonus": 5,
                },
            },
        },
        "minimalist": {
            "preset": "minimalist",
            "bodies": {
                "groups": {
                    "luminaries": True,
                    "classical": True,
                    "modern": False,
                    "dwarf": False,
                    "asteroids_major": False,
                }
            },
            "aspects": {
                "sets": {"ptolemaic": True, "minor": False},
                "detect_patterns": False,
            },
        },
        "horary_strict": {
            "preset": "traditional_western",
            "houses": {"system": "regiomontanus"},
            "bodies": {
                "groups": {
                    "luminaries": True,
                    "classical": True,
                    "modern": False,
                    "dwarf": False,
                    "centaurs": False,
                    "asteroids_major": False,
                }
            },
            "aspects": {
                "sets": {"ptolemaic": True, "minor": False, "harmonics": False},
                "detect_patterns": False,
                "orbs_global": 3.5,
                "orbs_by_aspect": {
                    "conjunction": 5.0,
                    "opposition": 5.0,
                    "trine": 4.0,
                    "square": 4.0,
                    "sextile": 3.0,
                },
                "orbs_by_body": {
                    "sun": 7.0,
                    "moon": 6.0,
                    "mercury": 4.0,
                    "venus": 4.0,
                    "mars": 4.0,
                    "jupiter": 3.5,
                    "saturn": 3.5,
                },
                "use_moiety": True,
            },
            "declinations": {"enabled": True, "orb_deg": 0.3},
            "dignities": {
                "scoring": "lilly",
                "weights": {
                    "domicile": 5,
                    "exaltation": 4,
                    "triplicity": 3,
                    "term": 2,
                    "face": 1,
                    "detriment": -5,
                    "fall": -4,
                    "angular": 5,
                    "succedent": 2,
                    "cadent": -2,
                    "retrograde": -6,
                    "combustion": -6,
                    "cazimi": 6,
                    "under_beams": -3,
                    "peregrine": -2,
                },
            },
            "timeline_ui": {"show_exact_only": True},
        },
        "counseling_modern": {
            "preset": "modern_western",
            "bodies": {
                "groups": {
                    "luminaries": True,
                    "classical": True,
                    "modern": True,
                    "dwarf": True,
                    "centaurs": False,
                    "asteroids_major": True,
                }
            },
            "aspects": {
                "sets": {"ptolemaic": True, "minor": True, "harmonics": False},
                "detect_patterns": True,
                "orbs_global": 6.5,
                "orbs_by_body": {
                    "sun": 10.0,
                    "moon": 9.0,
                    "mercury": 7.0,
                    "venus": 7.0,
                    "mars": 6.0,
                    "jupiter": 6.5,
                    "saturn": 6.5,
                },
                "weights_by_aspect": {
                    "conjunction": 5,
                    "opposition": 4,
                    "trine": 4,
                    "square": 3,
                    "sextile": 3,
                    "quincunx": 2,
                    "semisextile": 1,
                    "sesquisquare": 1,
                    "quintile": 1,
                    "biquintile": 1,
                },
            },
            "narrative": {
                "mode": "modern_psychological",
                "library": "western_basic",
                "tone": "teaching",
                "length": "medium",
                "verbosity": 0.7,
                "sources": {
                    "transits": True,
                    "progressions": True,
                    "midpoints": True,
                    "timelords": False,
                },
                "frameworks": {
                    "psychological": True,
                    "data_driven": True,
                    "jungian": False,
                },
                "disclaimers": True,
            },
            "reports": {"pdf_enabled": True, "template": "classic"},
        },
    }


def profiles_home() -> Path:
    """Return the directory containing persisted profiles."""

    return get_config_home() / PROFILES_DIRNAME


def list_profiles() -> dict[str, list[str]]:
    """Return a mapping of built-in and user profile names."""

    built_in = sorted(built_in_profiles().keys())
    user_profiles: list[str] = []
    directory = profiles_home()
    if directory.exists():
        for file_path in directory.glob("*.yaml"):
            user_profiles.append(file_path.stem)
    return {"built_in": built_in, "user": sorted(user_profiles)}


def load_profile_overlay(name: str) -> dict:
    """Load a profile overlay by name, preferring built-ins."""

    built_ins = built_in_profiles()
    if name in built_ins:
        return deepcopy(built_ins[name])
    profile_path = profiles_home() / f"{name}.yaml"
    if not profile_path.exists():
        raise FileNotFoundError(name)
    import yaml

    return yaml.safe_load(profile_path.read_text(encoding="utf-8")) or {}


def apply_profile_overlay(base: Settings, overlay: dict) -> Settings:
    """Return a new Settings object with ``overlay`` merged into ``base``."""

    def deep_merge(left: object, right: object) -> object:
        if isinstance(left, dict) and isinstance(right, dict):
            merged: dict = dict(left)
            for key, value in right.items():
                if key in merged:
                    merged[key] = deep_merge(merged[key], value)
                else:
                    merged[key] = deepcopy(value)
            return merged
        return deepcopy(right)

    merged_dict = deep_merge(base.model_dump(), overlay)
    return Settings(**merged_dict)


def save_user_profile(name: str, settings: Settings) -> Path:
    """Persist ``settings`` to a user-defined profile file."""

    directory = profiles_home()
    directory.mkdir(parents=True, exist_ok=True)
    profile_path = directory / f"{name}.yaml"
    import yaml

    profile_path.write_text(
        yaml.safe_dump(settings.model_dump(), sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return profile_path


def delete_user_profile(name: str) -> bool:
    """Delete the stored profile if it exists."""

    profile_path = profiles_home() / f"{name}.yaml"
    if profile_path.exists():
        profile_path.unlink()
        return True
    return False
