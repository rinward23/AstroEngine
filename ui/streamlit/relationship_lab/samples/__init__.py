"""Sample ChartPositions payloads for quick testing in the Relationship Lab."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class ChartSample:
    """Container describing a reusable ChartPositions dataset."""

    label: str
    positions: Mapping[str, float]


SAMPLES: dict[str, ChartSample] = {
    "NYC 1990-02-16": ChartSample(
        label="New York City — 1990-02-16 14:30 (regression dataset)",
        positions={
            "Sun": 327.824967,
            "Moon": 226.812266,
            "Mercury": 306.587384,
            "Venus": 292.269912,
            "Mars": 283.177018,
            "Jupiter": 90.915699,
            "Saturn": 290.924799,
            "Uranus": 278.287469,
            "Neptune": 283.6611,
            "Pluto": 227.785695,
        },
    ),
    "London 1985-07-13": ChartSample(
        label="London — 1985-07-13 09:00 (regression dataset)",
        positions={
            "Sun": 111.215606,
            "Moon": 61.184662,
            "Mercury": 137.755721,
            "Venus": 67.975138,
            "Mars": 112.558487,
            "Jupiter": 314.704774,
            "Saturn": 231.586352,
            "Uranus": 254.609143,
            "Neptune": 271.716086,
            "Pluto": 211.924831,
        },
    ),
    "Tokyo 2000-12-25": ChartSample(
        label="Tokyo — 2000-12-25 05:45 (regression dataset)",
        positions={
            "Sun": 273.465699,
            "Moon": 265.156077,
            "Mercury": 272.986165,
            "Venus": 319.107477,
            "Mars": 210.803963,
            "Jupiter": 62.824828,
            "Saturn": 54.933695,
            "Uranus": 318.320888,
            "Neptune": 305.085719,
            "Pluto": 253.51329,
        },
    ),
}

DEFAULT_PAIR = ("NYC 1990-02-16", "London 1985-07-13")


def sample_labels() -> list[str]:
    return list(SAMPLES.keys())


def get_sample(name: str) -> ChartSample:
    try:
        return SAMPLES[name]
    except KeyError as exc:  # pragma: no cover - defensive
        raise KeyError(f"Unknown sample '{name}'") from exc
