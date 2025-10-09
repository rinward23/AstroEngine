"""Tradition profiles and persistence helpers for horary judgement."""

from __future__ import annotations

import json
from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator

from ...infrastructure.paths import profiles_dir

__all__ = [
    "OrbPolicy",
    "DignityPolicy",
    "RadicalityPolicy",
    "TestimonyWeights",
    "ClassificationThresholds",
    "HoraryProfile",
    "DEFAULT_PROFILES",
    "load_profiles",
    "save_profiles",
    "get_profile",
    "list_profiles",
    "upsert_profile",
]


@dataclass(frozen=True)
class OrbPolicy:
    """Aspect orb allowances resolved for a tradition profile."""

    by_aspect: Mapping[str, float]
    by_body_mult: Mapping[str, float]


@dataclass(frozen=True)
class DignityPolicy:
    """Essential dignity weights applied during testimony scoring."""

    weights: Mapping[str, float]


@dataclass(frozen=True)
class RadicalityPolicy:
    """Thresholds governing radicality checks."""

    asc_early_deg: float
    asc_late_deg: float
    south_node_on_asc_orb: float


@dataclass(frozen=True)
class TestimonyWeights:
    """Weights applied to testimony contributions."""

    entries: Mapping[str, float]


@dataclass(frozen=True)
class ClassificationThresholds:
    """Score thresholds for translating totals into outcome categories."""

    yes: float
    qualified: float
    weak: float


class HoraryProfile(BaseModel):
    """Serializable policy definition applied to horary judgements."""

    name: str
    orbs: dict[str, dict[str, float]] = Field(default_factory=dict)
    dignities: dict[str, float] = Field(default_factory=dict)
    radicality: dict[str, float] = Field(default_factory=dict)
    testimony_weights: dict[str, float] = Field(default_factory=dict)
    classification_thresholds: dict[str, float] = Field(default_factory=dict)

    model_config = {
        "extra": "forbid",
        "populate_by_name": True,
    }

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Profile name must not be empty")
        return stripped

    def orb_policy(self) -> OrbPolicy:
        by_aspect = {k.lower(): float(v) for k, v in self.orbs.get("by_aspect", {}).items()}
        by_body = {k.title(): float(v) for k, v in self.orbs.get("by_body_mult", {}).items()}
        return OrbPolicy(by_aspect=by_aspect, by_body_mult=by_body)

    def dignity_policy(self) -> DignityPolicy:
        return DignityPolicy(weights={k.lower(): float(v) for k, v in self.dignities.items()})

    def radicality_policy(self) -> RadicalityPolicy:
        data = {k: float(v) for k, v in self.radicality.items()}
        return RadicalityPolicy(
            asc_early_deg=data.get("asc_early_deg", 3.0),
            asc_late_deg=data.get("asc_late_deg", 27.0),
            south_node_on_asc_orb=data.get("south_node_on_asc_orb", 3.0),
        )

    def testimony_policy(self) -> TestimonyWeights:
        return TestimonyWeights(entries={k: float(v) for k, v in self.testimony_weights.items()})

    def thresholds(self) -> ClassificationThresholds:
        data = {k: float(v) for k, v in self.classification_thresholds.items()}
        return ClassificationThresholds(
            yes=data.get("yes", 70.0),
            qualified=data.get("qualified", 50.0),
            weak=data.get("weak", 30.0),
        )


_DEFAULT_PROFILE_PATH = profiles_dir() / "horary_profiles.json"


def _default_profiles() -> dict[str, HoraryProfile]:
    base = {
        "Lilly": HoraryProfile(
            name="Lilly",
            orbs={
                "by_aspect": {
                    "conjunction": 8.0,
                    "sextile": 4.0,
                    "square": 6.0,
                    "trine": 6.0,
                    "opposition": 8.0,
                },
                "by_body_mult": {
                    "Sun": 1.25,
                    "Moon": 1.5,
                    "Saturn": 0.9,
                },
            },
            dignities={
                "domicile": 5.0,
                "exaltation": 4.0,
                "triplicity": 3.0,
                "term": 2.0,
                "face": 1.0,
                "detriment": -5.0,
                "fall": -4.0,
            },
            radicality={
                "asc_early_deg": 3.0,
                "asc_late_deg": 27.0,
                "south_node_on_asc_orb": 3.0,
            },
            testimony_weights={
                "applying_with_reception": 20.0,
                "applying_no_reception": 12.0,
                "translation": 10.0,
                "collection": 8.0,
                "prohibition": -15.0,
                "moon_next_good": 8.0,
                "malefic_on_angle": -10.0,
            },
            classification_thresholds={
                "yes": 70.0,
                "qualified": 50.0,
                "weak": 30.0,
            },
        ),
        "Bonatti": HoraryProfile(
            name="Bonatti",
            orbs={
                "by_aspect": {
                    "conjunction": 7.0,
                    "sextile": 4.0,
                    "square": 6.0,
                    "trine": 7.0,
                    "opposition": 8.0,
                },
                "by_body_mult": {
                    "Sun": 1.2,
                    "Moon": 1.7,
                    "Saturn": 1.0,
                    "Jupiter": 1.1,
                },
            },
            dignities={
                "domicile": 5.0,
                "exaltation": 4.0,
                "triplicity": 3.0,
                "term": 2.0,
                "face": 1.0,
                "detriment": -5.0,
                "fall": -4.0,
            },
            radicality={
                "asc_early_deg": 2.0,
                "asc_late_deg": 28.0,
                "south_node_on_asc_orb": 2.0,
            },
            testimony_weights={
                "applying_with_reception": 24.0,
                "applying_no_reception": 10.0,
                "translation": 12.0,
                "collection": 10.0,
                "prohibition": -18.0,
                "moon_next_good": 6.0,
                "malefic_on_angle": -12.0,
            },
            classification_thresholds={
                "yes": 72.0,
                "qualified": 55.0,
                "weak": 35.0,
            },
        ),
    }
    return {name.lower(): profile for name, profile in base.items()}


DEFAULT_PROFILES: Mapping[str, HoraryProfile] = _default_profiles()


def load_profiles(storage_path: Path | None = None) -> dict[str, HoraryProfile]:
    """Load profiles from disk when available, otherwise defaults."""

    path = storage_path or _DEFAULT_PROFILE_PATH
    profiles: MutableMapping[str, HoraryProfile] = dict(DEFAULT_PROFILES)
    if path.exists():
        try:
            payload = json.loads(path.read_text("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid horary profile file {path}: {exc}") from exc
        for raw in payload:
            try:
                profile = HoraryProfile.model_validate(raw)
            except ValidationError as exc:
                raise ValueError(f"Invalid profile entry in {path}: {exc}") from exc
            profiles[profile.name.lower()] = profile
    return dict(profiles)


def save_profiles(
    profiles: Mapping[str, HoraryProfile], storage_path: Path | None = None
) -> None:
    """Persist profiles to disk for API customisation."""

    path = storage_path or _DEFAULT_PROFILE_PATH
    serialisable: list[dict[str, Any]] = [
        profile.model_dump(mode="json") for profile in profiles.values()
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(serialisable, indent=2, sort_keys=True), "utf-8")


def get_profile(name: str, storage_path: Path | None = None) -> HoraryProfile:
    """Return a profile by case-insensitive name."""

    profiles = load_profiles(storage_path)
    key = name.strip().lower()
    if key not in profiles:
        available = ", ".join(sorted(profiles))
        raise KeyError(f"Unknown horary profile '{name}'. Available: {available}")
    return profiles[key]


def list_profiles(storage_path: Path | None = None) -> tuple[HoraryProfile, ...]:
    """Return all available profiles sorted by name."""

    profiles = load_profiles(storage_path)
    return tuple(sorted(profiles.values(), key=lambda p: p.name.lower()))


def upsert_profile(
    payload: Mapping[str, Any], storage_path: Path | None = None
) -> HoraryProfile:
    """Insert or update a profile definition stored on disk."""

    profile = HoraryProfile.model_validate(payload)
    profiles = load_profiles(storage_path)
    profiles[profile.name.lower()] = profile
    save_profiles(profiles, storage_path)
    return profile
