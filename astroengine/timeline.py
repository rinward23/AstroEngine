"""Dynamic transit corridor timeline utilities."""

from __future__ import annotations

import datetime as dt
from collections.abc import Sequence
from dataclasses import dataclass, field

from .refine import CorridorModel, branch_sensitive_angles

__all__ = ["TransitWindow", "merge_windows", "window_envelope"]


@dataclass(frozen=True)
class TransitWindow:
    """Soft time window annotated with a membership curve and metadata."""

    start: dt.datetime
    peak: dt.datetime
    end: dt.datetime
    corridor: CorridorModel
    confidence: float = 1.0
    sensitive_angles: Sequence[float] = field(default_factory=tuple)
    metadata: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.start > self.end:
            raise ValueError("TransitWindow start must not be after end.")
        if not (self.start <= self.peak <= self.end):
            raise ValueError("TransitWindow peak must lie within start/end bounds.")

    def duration(self) -> dt.timedelta:
        return self.end - self.start

    def time_membership(self, moment: dt.datetime) -> float:
        """Return the corridor membership for ``moment`` mapped into degrees."""

        reference = moment.replace(tzinfo=dt.UTC)
        peak = self.peak.replace(tzinfo=dt.UTC)
        delta_hours = abs((reference - peak).total_seconds()) / 3600.0
        if "hours_per_degree" not in self.metadata:
            raise KeyError("TransitWindow metadata requires 'hours_per_degree'.")
        hours_per_degree = float(self.metadata["hours_per_degree"])
        if hours_per_degree <= 0.0:
            raise ValueError("hours_per_degree must be positive.")
        delta_deg = delta_hours / hours_per_degree
        return self.corridor.membership(delta_deg)

    def describe(self) -> dict[str, object]:
        payload = {
            "start": self.start.isoformat(),
            "peak": self.peak.isoformat(),
            "end": self.end.isoformat(),
            "confidence": float(max(min(self.confidence, 1.0), 0.0)),
            "corridor": self.corridor.describe(),
            "sensitive_angles": list(self.sensitive_angles),
        }
        if self.metadata:
            payload["metadata"] = dict(self.metadata)
        return payload


def window_envelope(
    center_iso: str,
    width_deg: float,
    *,
    hours_per_degree: float,
    softness: float = 0.5,
    metadata: dict[str, object] | None = None,
) -> TransitWindow:
    """Factory helper creating a :class:`TransitWindow` around ``center_iso``."""

    if hours_per_degree <= 0.0:
        raise ValueError("hours_per_degree must be > 0 to derive a time window.")
    center_dt = dt.datetime.fromisoformat(center_iso.replace("Z", "+00:00"))
    half_hours = width_deg * hours_per_degree
    start = center_dt - dt.timedelta(hours=half_hours)
    end = center_dt + dt.timedelta(hours=half_hours)
    corridor = CorridorModel(
        center_iso=center_iso,
        width_deg=width_deg,
        softness=softness,
        metadata=metadata or {},
    )
    anchor_angle = float((metadata or {}).get("base_angle_deg", 0.0))
    sensitive = branch_sensitive_angles(anchor_angle)
    return TransitWindow(
        start=start,
        peak=center_dt,
        end=end,
        corridor=corridor,
        confidence=metadata.get("confidence", 1.0) if metadata else 1.0,
        sensitive_angles=sensitive,
        metadata={"hours_per_degree": hours_per_degree, **(metadata or {})},
    )


def merge_windows(windows: Sequence[TransitWindow]) -> list[TransitWindow]:
    """Merge overlapping windows by retaining the highest confidence corridor."""

    if not windows:
        return []
    ordered = sorted(windows, key=lambda w: (w.start, -w.confidence))
    merged: list[TransitWindow] = [ordered[0]]
    for window in ordered[1:]:
        current = merged[-1]
        if window.start <= current.end:
            if window.confidence > current.confidence:
                merged[-1] = TransitWindow(
                    start=current.start,
                    peak=window.peak,
                    end=max(current.end, window.end),
                    corridor=window.corridor,
                    confidence=window.confidence,
                    sensitive_angles=window.sensitive_angles
                    or current.sensitive_angles,
                    metadata={**current.metadata, **window.metadata},
                )
            else:
                merged[-1] = TransitWindow(
                    start=current.start,
                    peak=current.peak,
                    end=max(current.end, window.end),
                    corridor=current.corridor,
                    confidence=current.confidence,
                    sensitive_angles=current.sensitive_angles
                    or window.sensitive_angles,
                    metadata={**window.metadata, **current.metadata},
                )
        else:
            merged.append(window)
    return merged
