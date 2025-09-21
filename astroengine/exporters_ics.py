# >>> AUTO-GEN BEGIN: exporter-ics v1.0
from __future__ import annotations
from typing import Iterable

try:
    from ics import Calendar, Event  # type: ignore
except Exception as e:  # pragma: no cover
    Calendar = None  # type: ignore
    Event = None  # type: ignore


def write_ics(events: Iterable[object], path: str, title: str = "AstroEngine Events") -> str:
    """Write events (with .ts and .__class__.__name__) to an .ics file. Returns path."""
    if Calendar is None:
        raise RuntimeError("ICS exporter not available. Install extras: astroengine[exporters]")
    cal = Calendar()
    for ev in events:
        e = Event()
        e.name = f"{ev.__class__.__name__}"
        e.begin = getattr(ev, 'ts')
        cal.events.add(e)
    with open(path, 'w', encoding='utf-8') as f:
        f.writelines(cal)
    return path
# >>> AUTO-GEN END: exporter-ics v1.0
