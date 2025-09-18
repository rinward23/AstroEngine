"""Command line helpers for the transit module."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import click

from .detectors import compute_orb, detect_ecliptic_contacts
from .profiles import build_default_profiles
from .refine import refine_exact

ISO_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def _parse_iso8601(value: str) -> datetime:
    try:
        dt = datetime.strptime(value, ISO_FORMAT)
    except ValueError as exc:  # pragma: no cover - validated via click
        raise click.BadParameter(f"Invalid timestamp '{value}'") from exc
    return dt.replace(tzinfo=timezone.utc)


def _format_iso8601(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime(ISO_FORMAT)


# <<< AUTO-GEN START: CLI v1.0 (mock scan) >>>
class MockLinearProvider:
    """Linear motion provider used for demonstration purposes."""

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
        self.t0 = _parse_iso8601(t0_iso)

    def ecliptic_state(self, t_iso: str, **_: object) -> dict[str, dict[str, float]]:
        target = _parse_iso8601(t_iso)
        delta_days = (target - self.t0).total_seconds() / 86400.0
        lon = (self.lon0_deg + self.speed_deg_per_day * delta_days) % 360.0
        return {
            self.body: {
                "lon_deg": lon,
                "lon_speed_deg_per_day": self.speed_deg_per_day,
            }
        }


@click.group()
def main() -> None:
    """Transit command line utilities."""


@main.command("scan-mock")
@click.option("--start", "start_iso", required=True, help="Scan window start (UTC)")
@click.option("--end", "end_iso", required=True, help="Scan window end (UTC)")
@click.option(
    "--step",
    type=int,
    default=6,
    show_default=True,
    help="Tick spacing in hours",
)
@click.option("--body", "body_name", required=True, help="Transiting body name")
@click.option("--lon0", type=float, required=True, help="Body longitude at start")
@click.option("--speed", type=float, required=True, help="Body speed in deg/day")
@click.option("--natal-point", "natal_point", required=True, help="Natal point name")
@click.option("--natal-lon", type=float, required=True, help="Natal longitude")
@click.option(
    "--aspect",
    type=click.Choice(
        [
            "conjunction",
            "sextile",
            "square",
            "trine",
            "opposition",
            "semisextile",
            "semisquare",
            "sesquisquare",
            "quincunx",
        ]
    ),
    required=True,
    help="Aspect to track",
)
def scan_mock(
    start_iso: str,
    end_iso: str,
    step: int,
    body_name: str,
    lon0: float,
    speed: float,
    natal_point: str,
    natal_lon: float,
    aspect: str,
) -> None:
    """Run a mock transit scan using the linear provider."""

    start_dt = _parse_iso8601(start_iso)
    end_dt = _parse_iso8601(end_iso)
    if end_dt < start_dt:
        raise click.BadParameter("--end must be after --start")

    provider = MockLinearProvider(body_name, lon0, speed, start_iso)
    orb_policy, severity_model = build_default_profiles()
    natal: Dict[str, float | str] = {"name": natal_point, "lon_deg": float(natal_lon)}

    tick = start_dt
    step_delta = timedelta(hours=step)
    while tick <= end_dt:
        state_raw = provider.ecliptic_state(_format_iso8601(tick))
        state: Dict[str, Any] = dict(state_raw)
        state["__timestamp__"] = tick
        events = detect_ecliptic_contacts(state, natal, [aspect], orb_policy)
        for event in events:
            t_exact = refine_exact(provider, event, natal)
            exact_raw = provider.ecliptic_state(_format_iso8601(t_exact))
            exact_state: Dict[str, Any] = dict(exact_raw)
            exact_state["__timestamp__"] = t_exact
            lon = float(exact_state[event.transiting_body]["lon_deg"])
            natal_lon_val = float(natal["lon_deg"])
            orb = abs(compute_orb(lon, natal_lon_val, event.aspect))
            metadata = dict(event.metadata)
            metadata["signed_orb"] = compute_orb(lon, natal_lon_val, event.aspect)
            refined = event.copy_with(timestamp=t_exact, orb_deg=orb, metadata=metadata)
            severity = severity_model.score_event(refined, orb_policy)
            payload = {
                "t_exact": _format_iso8601(t_exact),
                "aspect": refined.aspect,
                "transiting_body": refined.transiting_body,
                "natal_point": refined.natal_point,
                "orb_deg": round(refined.orb_deg, 3),
                "severity": round(severity, 3),
                "family": refined.family,
            }
            click.echo(json.dumps(payload))
        tick += step_delta


# <<< AUTO-GEN END: CLI v1.0 (mock scan) >>>

if __name__ == "__main__":  # pragma: no cover
    main()
