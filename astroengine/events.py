"""Structured event records produced by AstroEngine detectors."""



__all__ = [
    "BaseEvent",
    "LunationEvent",
    "EclipseEvent",
    "StationEvent",
    "ReturnEvent",
    "ProgressionEvent",
    "DirectionEvent",
    "ProfectionEvent",
]


@dataclass(frozen=True)
class BaseEvent:



@dataclass(frozen=True)
class LunationEvent(BaseEvent):



@dataclass(frozen=True)
class EclipseEvent(BaseEvent):



@dataclass(frozen=True)
class StationEvent(BaseEvent):



@dataclass(frozen=True)
class ReturnEvent(BaseEvent):



@dataclass(frozen=True)
class ProgressionEvent(BaseEvent):



@dataclass(frozen=True)
class DirectionEvent(BaseEvent):



@dataclass(frozen=True)
class ProfectionEvent(BaseEvent):

