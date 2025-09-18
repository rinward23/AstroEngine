from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from astroengine.transit.detectors import compute_orb, detect_ecliptic_contacts
from astroengine.transit.profiles import build_default_profiles
from astroengine.transit.refine import refine_exact

ISO_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def _parse_iso(value: str) -> datetime:
    return datetime.strptime(value, ISO_FORMAT).replace(tzinfo=timezone.utc)


def _format_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime(ISO_FORMAT)


# <<< AUTO-GEN START: Transit Acceptance v1.0 >>>
class MockLinearProvider:
    def __init__(
        self,
        body: str,
        lon0_deg: float,
        speed_deg_per_day: float,
        t0_iso: str,
    ) -> None:
        self.body = body
        self.lon0_deg = lon0_deg % 360.0
        self.speed_deg_per_day = speed_deg_per_day
        self.t0 = _parse_iso(t0_iso)

    def ecliptic_state(self, t_iso: str, **_: object) -> dict[str, dict[str, float]]:
        target = _parse_iso(t_iso)
        delta_days = (target - self.t0).total_seconds() / 86400.0
        lon = (self.lon0_deg + self.speed_deg_per_day * delta_days) % 360.0
        return {
            self.body: {
                "lon_deg": lon,
                "lon_speed_deg_per_day": self.speed_deg_per_day,
            }
        }


def test_transit_acceptance() -> None:
    start_iso = "2025-01-01T00:00:00Z"
    end_iso = "2025-01-31T00:00:00Z"
    provider = MockLinearProvider("Mars", 50.0, 6.0, start_iso)
    orb_policy, severity_model = build_default_profiles()
    start_dt = _parse_iso(start_iso)
    end_dt = _parse_iso(end_iso)
    step = timedelta(hours=12)

    natal: Dict[str, float | str] = {"name": "Venus", "lon_deg": 100.0}
    aspect = "square"

    events = []
    tick = start_dt
    while tick <= end_dt:
        raw_state = provider.ecliptic_state(_format_iso(tick))
        state: Dict[str, Any] = dict(raw_state)
        state["__timestamp__"] = tick
        events.extend(detect_ecliptic_contacts(state, natal, [aspect], orb_policy))
        tick += step

    assert events, "Expected at least one transit contact"

    refined_events = []
    for event in events:
        t_exact = refine_exact(provider, event, natal)
        exact_raw = provider.ecliptic_state(_format_iso(t_exact))
        exact_state: Dict[str, Any] = dict(exact_raw)
        exact_state["__timestamp__"] = t_exact
        lon = float(exact_state[event.transiting_body]["lon_deg"])
        natal_lon_val = float(natal["lon_deg"])
        signed_orb = compute_orb(lon, natal_lon_val, event.aspect)
        metadata = dict(event.metadata)
        metadata["signed_orb"] = signed_orb
        refined = event.copy_with(
            timestamp=t_exact,
            orb_deg=abs(signed_orb),
            metadata=metadata,
        )
        severity = severity_model.score_event(refined, orb_policy)
        refined.metadata["severity"] = severity
        refined_events.append(refined)

    peak_event = max(refined_events, key=lambda item: item.metadata["severity"])

    orb_allow = orb_policy(peak_event.transiting_body, peak_event.natal_point, aspect)
    assert peak_event.orb_deg <= orb_allow

    before_time = peak_event.timestamp - step
    after_time = peak_event.timestamp + step

    def _severity_for(moment: datetime) -> float:
        state = provider.ecliptic_state(_format_iso(moment))
        lon_val = float(state[peak_event.transiting_body]["lon_deg"])
        natal_lon_val = float(natal["lon_deg"])
        diff = abs(compute_orb(lon_val, natal_lon_val, aspect))
        return severity_model.score_from_diff(
            diff,
            orb_allow,
            aspect,
            peak_event.transiting_body,
            partile=False,
        )

    before_severity = _severity_for(before_time)
    after_severity = _severity_for(after_time)

    assert peak_event.metadata["severity"] >= before_severity
    assert peak_event.metadata["severity"] >= after_severity
    assert peak_event.orb_deg <= min(orb_allow, 0.01)


# <<< AUTO-GEN END: Transit Acceptance v1.0 >>>
