"""Collection utilities for assembling datasets from AstroEngine runs."""

from __future__ import annotations

from typing import List

from ..engine import scan_contacts


def collect_events(args) -> List[object]:
    """Collect events for dataset exports based on CLI arguments.

    Currently supports the ``transits`` command by reusing :func:`scan_contacts`.
    """

    if getattr(args, "command", None) == "transits":
        return scan_contacts(
            start_iso=args.start,
            end_iso=args.end,
            moving=args.moving,
            target=args.target,
            provider_name=args.provider,
            decl_parallel_orb=args.decl_orb,
            decl_contra_orb=args.decl_orb,
            antiscia_orb=args.mirror_orb,
            contra_antiscia_orb=args.mirror_orb,
            step_minutes=args.step,
            aspects_policy_path=args.aspects_policy,
        )

    start_utc = getattr(args, "start_utc", None)
    end_utc = getattr(args, "end_utc", None)
    detectors_enabled = any(
        getattr(args, flag, False)
        for flag in ("lunations", "stations", "returns", "progressions", "directions")
    )
    if start_utc and end_utc and detectors_enabled:
        from ..detectors.common import iso_to_jd
        try:
            from ..detectors import (
                find_lunations,
                find_stations,
                solar_lunar_returns,
                secondary_progressions,
                solar_arc_directions,
            )
        except ImportError as exc:  # pragma: no cover - defensive fallback
            raise RuntimeError("detector implementations unavailable for dataset export") from exc

        start_jd = iso_to_jd(start_utc)
        end_jd = iso_to_jd(end_utc)
        events: List[object] = []
        if getattr(args, "lunations", False):
            events.extend(find_lunations(start_jd, end_jd))
        if getattr(args, "stations", False):
            events.extend(find_stations(start_jd, end_jd, None))
        if getattr(args, "returns", False) and getattr(args, "natal_utc", None):
            natal_jd = iso_to_jd(args.natal_utc)
            which = getattr(args, "return_kind", "solar")
            events.extend(solar_lunar_returns(natal_jd, start_jd, end_jd, which))
        if getattr(args, "progressions", False) and getattr(args, "natal_utc", None):
            events.extend(secondary_progressions(args.natal_utc, start_utc, end_utc))
        if getattr(args, "directions", False) and getattr(args, "natal_utc", None):
            events.extend(solar_arc_directions(args.natal_utc, start_utc, end_utc))
        return events

    raise RuntimeError("collect_events currently supports the transits command or detector flags with start/end timestamps")
