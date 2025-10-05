"""Narrative profile overlay helpers exposed under :mod:`astroengine.config`."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Mapping, MutableMapping

import yaml

from .settings import NarrativeCfg, get_config_home

__all__ = [
    "NARRATIVE_PROFILES_DIRNAME",
    "built_in_narrative_profiles",
    "narrative_profiles_home",
    "list_narrative_profiles",
    "load_narrative_profile_overlay",
    "save_user_narrative_profile",
]


NARRATIVE_PROFILES_DIRNAME = "narrative_profiles"


def _default_esoteric() -> Dict[str, Any]:
    return {
        "tarot_enabled": False,
        "tarot_deck": "rws",
        "numerology_enabled": False,
        "numerology_system": "pythagorean",
    }


_BUILT_IN_NARRATIVE_PROFILES: Dict[str, Dict[str, Any]] = {
    "modern_psychological": {
        "narrative": {
            "mode": "modern_psychological",
            "library": "western_basic",
            "tone": "teaching",
            "length": "medium",
            "verbosity": 0.65,
            "sources": {
                "transits": True,
                "progressions": True,
                "midpoints": True,
                "timelords": True,
            },
            "frameworks": {
                "psychological": True,
                "jungian": False,
                "data_driven": True,
            },
            "esoteric": _default_esoteric(),
            "disclaimers": True,
        }
    },
    "data_minimal": {
        "narrative": {
            "mode": "data_minimal",
            "library": "none",
            "tone": "brief",
            "length": "short",
            "verbosity": 0.3,
            "sources": {
                "transits": True,
                "progressions": False,
                "midpoints": False,
                "timelords": False,
            },
            "frameworks": {
                "psychological": False,
                "jungian": False,
                "data_driven": True,
            },
            "esoteric": _default_esoteric(),
            "disclaimers": False,
        }
    },
    "jungian_archetypal": {
        "narrative": {
            "mode": "jungian_archetypal",
            "library": "western_basic",
            "tone": "teaching",
            "length": "long",
            "verbosity": 0.75,
            "sources": {
                "transits": True,
                "progressions": True,
                "midpoints": True,
                "timelords": True,
            },
            "frameworks": {
                "psychological": True,
                "jungian": True,
                "mythic": True,
            },
            "esoteric": {
                "tarot_enabled": True,
                "tarot_deck": "thoth",
                "numerology_enabled": True,
                "numerology_system": "pythagorean",
            },
            "disclaimers": True,
        }
    },
    "hellenistic_sober": {
        "narrative": {
            "mode": "hellenistic_sober",
            "library": "hellenistic",
            "tone": "neutral",
            "length": "medium",
            "verbosity": 0.5,
            "sources": {
                "transits": True,
                "lots": True,
                "sect": True,
            },
            "frameworks": {
                "traditional": True,
                "psychological": False,
                "data_driven": False,
            },
            "esoteric": _default_esoteric(),
            "disclaimers": True,
        }
    },
}


def built_in_narrative_profiles() -> Dict[str, Dict[str, Any]]:
    """Return a deep copy of built-in narrative overlays."""

    return deepcopy(_BUILT_IN_NARRATIVE_PROFILES)


def narrative_profiles_home() -> Path:
    """Return the directory containing user narrative profiles."""

    return get_config_home() / NARRATIVE_PROFILES_DIRNAME


def list_narrative_profiles() -> Dict[str, list[str]]:
    """Return available built-in and user narrative profile identifiers."""

    built_in = sorted(built_in_narrative_profiles().keys())
    user_profiles: list[str] = []
    directory = narrative_profiles_home()
    if directory.exists():
        for file_path in directory.glob("*.yaml"):
            user_profiles.append(file_path.stem)
    return {"built_in": built_in, "user": sorted(user_profiles)}


def load_narrative_profile_overlay(name: str) -> Dict[str, Any]:
    """Load a narrative overlay from built-ins or disk."""

    built_ins = built_in_narrative_profiles()
    if name in built_ins:
        return deepcopy(built_ins[name])
    path = narrative_profiles_home() / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(name)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data or {}


def save_user_narrative_profile(
    name: str, narrative: NarrativeCfg | Mapping[str, Any] | MutableMapping[str, Any]
) -> Path:
    """Persist a user-defined narrative overlay to disk."""

    directory = narrative_profiles_home()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.yaml"

    if isinstance(narrative, NarrativeCfg):
        payload: Dict[str, Any] = narrative.model_dump()
    else:
        payload = dict(narrative)

    path.write_text(
        yaml.safe_dump({"narrative": payload}, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return path
