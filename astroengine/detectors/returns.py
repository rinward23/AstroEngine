# >>> AUTO-GEN BEGIN: detector-returns v1.0
from __future__ import annotations
from typing import List

from .common import body_lon, delta_deg, find_root
from ..events import ReturnEvent


def _body_for_kind(kind: str) -> str:
    if kind not in {"solar", "lunar"}:
        raise ValueError(f"Unsupported return kind: {kind}")
    return "sun" if kind == "solar" else "moon"


def solar_lunar_returns(
    natal_jd: float,
    start_jd: float,
    end_jd: float,
    kind: str = "solar",
) -> List[ReturnEvent]:
    if end_jd <= start_jd:
        return []

    body = _body_for_kind(kind)
    natal_lon = body_lon(natal_jd, body)
    step = 7.0 if body == "sun" else 0.5
    events: List[ReturnEvent] = []
    t0 = start_jd
    delta0 = delta_deg(body_lon(t0, body), natal_lon)
    while t0 < end_jd:
        t1 = min(t0 + step, end_jd)
        delta1 = delta_deg(body_lon(t1, body), natal_lon)
        if abs(delta0) < 1e-5:
            root = t0
        elif delta0 * delta1 > 0:
            t0, delta0 = t1, delta1
            continue
        else:
            root = find_root(
                lambda jd: delta_deg(body_lon(jd, body), natal_lon),
                t0,
                t1,
                tol=1e-6,
            )
        longitude = body_lon(root, body)
        if events and abs(events[-1].ts - root) < 1e-4 and events[-1].body == body:
            t0, delta0 = t1, delta1
            continue
        events.append(
            ReturnEvent(
                ts=root,
                body=body,
                kind=kind,
                longitude=longitude,
            )
        )
        t0, delta0 = t1, delta1
    events.sort(key=lambda ev: ev.ts)
    return events
# >>> AUTO-GEN END: detector-returns v1.0
