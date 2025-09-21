"""Event dataclasses shared across detectors and exporters."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class EventBase:
    ts: str
    kind: Optional[str] = None
    method: Optional[str] = None
    moving_body: Optional[str] = None
    static_body: Optional[str] = None
    aspect: Optional[int] = None
    body: Optional[str] = None
    sign: Optional[str] = None
    lord: Optional[str] = None
    start_ts: Optional[str] = None
    end_ts: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def timestamp(self) -> str:
        return self.ts

    @property
    def when_iso(self) -> str:
        return self.ts

    @property
    def moving(self) -> Optional[str]:
        return self.moving_body

    @property
    def target(self) -> Optional[str]:
        return self.static_body

    @property
    def event_type(self) -> str:
        name = self.__class__.__name__
        return name[:-5].lower() if name.endswith("Event") else name.lower()


@dataclass
class LunationEvent(EventBase):
    pass


@dataclass
class EclipseEvent(EventBase):
    pass


@dataclass
class StationEvent(EventBase):
    pass


@dataclass
class ReturnEvent(EventBase):
    pass


@dataclass
class ProgressionEvent(EventBase):
    pass


@dataclass
class DirectionEvent(EventBase):
    pass


@dataclass
class ProfectionEvent(EventBase):
    pass
