"""Profiles registry and helpers for AstroEngine settings."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Dict

from .settings import Settings, get_config_home

PROFILES_DIRNAME = "profiles"


def built_in_profiles() -> Dict[str, dict]:
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
    }


def profiles_home() -> Path:
    """Return the directory containing persisted profiles."""

    return get_config_home() / PROFILES_DIRNAME


def list_profiles() -> Dict[str, list[str]]:
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
