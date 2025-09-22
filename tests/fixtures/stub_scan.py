"""Stub scan entrypoints for tests and Streamlit harnesses."""

from __future__ import annotations

from typing import Iterable, List, Mapping, Sequence


def fake_scan(
    *,
    start_utc: str,
    end_utc: str,
    moving: Sequence[str],
    targets: Sequence[str],
    provider: str | None = None,
    profile_id: str | None = None,
    step_minutes: int = 60,
    sidereal: bool | None = None,
    ayanamsha: str | None = None,
    detectors: Iterable[str] | None = None,
    target_frames: Iterable[str] | None = None,
) -> List[Mapping[str, object]]:
    """Return a deterministic payload representing a completed scan."""

    detectors_list = sorted(detectors or [])
    frames_list = sorted(target_frames or [])

    summary = {
        "ts": start_utc,
        "moving": moving[0] if moving else "Sun",
        "target": targets[0] if targets else "natal_Sun",
        "aspect": "conjunction",
        "orb": 0.0,
        "applying": True,
        "score": 1.0,
        "meta": {
            "provider": provider or "auto",
            "profile_id": profile_id or "default",
            "sidereal": bool(sidereal),
            "ayanamsha": ayanamsha,
            "detectors": detectors_list,
            "frames": frames_list,
            "step_minutes": step_minutes,
        },
    }

    follow_up = {
        "ts": end_utc,
        "moving": (moving[1] if len(moving) > 1 else summary["moving"]),
        "target": (targets[1] if len(targets) > 1 else summary["target"]),
        "aspect": "trine",
        "orb": 1.25,
        "applying": False,
        "score": 0.75,
        "meta": {
            "provider": provider or "auto",
            "profile_id": profile_id or "default",
            "sidereal": bool(sidereal),
            "ayanamsha": ayanamsha,
            "detectors": detectors_list,
            "frames": frames_list,
            "step_minutes": step_minutes,
        },
    }

    return [summary, follow_up]


__all__ = ["fake_scan"]
