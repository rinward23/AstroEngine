"""Core data structures for timelord period calculations."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime

__all__ = ["TimelordPeriod", "TimelordStack"]


@dataclass(frozen=True)
class TimelordPeriod:
    """Represents a single bounded timelord period."""

    system: str
    level: str
    ruler: str
    start: datetime
    end: datetime
    metadata: Mapping[str, object] = field(default_factory=dict)

    def contains(self, moment: datetime) -> bool:
        """Return ``True`` when ``moment`` lies within the period bounds."""

        reference = moment.astimezone(UTC)
        return self.start <= reference < self.end

    def midpoint(self) -> datetime:
        """Return the midpoint timestamp between ``start`` and ``end``."""

        delta = self.end - self.start
        return self.start + (delta / 2)

    def to_dict(self) -> dict[str, object]:
        """Return a serialisable mapping describing the period."""

        return {
            "system": self.system,
            "level": self.level,
            "ruler": self.ruler,
            "start": self.start.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            "end": self.end.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class TimelordStack:
    """Container describing the active timelord periods at a given moment."""

    moment: datetime
    periods: tuple[TimelordPeriod, ...]

    def rulers(self) -> list[str]:
        """Return the ordered list of active rulers."""

        return [period.ruler for period in self.periods]

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serialisable payload."""

        return {
            "moment": self.moment.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            "periods": [period.to_dict() for period in self.periods],
        }

    def iter_periods(self) -> Iterable[TimelordPeriod]:
        """Iterate over contained periods."""

        return iter(self.periods)
