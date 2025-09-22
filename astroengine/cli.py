"""Command line interface for AstroEngine."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence, Any


from . import engine as engine_module

from .chart.config import (
    ChartConfig,
    DEFAULT_SIDEREAL_AYANAMSHA,
    SUPPORTED_AYANAMSHAS,
    VALID_ZODIAC_SYSTEMS,
)

from .chart.config import ChartConfig, VALID_HOUSE_SYSTEMS, VALID_ZODIAC_SYSTEMS
from .detectors.ingress import find_ingresses
from .engine import events_to_dicts, scan_contacts
from .astro.declination import available_antiscia_axes
from .ephemeris import SwissEphemerisAdapter
from .narrative import summarize_top_events


from .pipeline.provision import provision_ephemeris, is_provisioned  # ENSURE-LINE

from .providers import list_providers
from .timelords.dashas import compute_vimshottari_dasha
from .timelords.zr import compute_zodiacal_releasing
from .validation import (
    SchemaValidationError,
    available_schema_keys,
    validate_payload,
)

from .userdata.vault import Natal, save_natal, load_natal, list_natals, delete_natal  # ENSURE-LINE
from .ux.plugins import setup_cli as setup_plugins



def _augment_parser_with_natals(parser: argparse.ArgumentParser) -> None:
    if getattr(parser, "_ae_natals_added", False):
        return
    subparsers = _ensure_subparsers(parser)
    natal = subparsers.add_parser("natal", help="Manage the natal vault")
    natal_sub = natal.add_subparsers(dest="natal_command")
    natal_sub.required = True

    natal_list = natal_sub.add_parser("list", help="List stored natal chart identifiers")
    natal_list.set_defaults(func=cmd_natal_list)

    natal_show = natal_sub.add_parser("show", help="Display a stored natal chart")
    natal_show.add_argument("natal_id")
    natal_show.set_defaults(func=cmd_natal_show)

    natal_save = natal_sub.add_parser("save", help="Persist a natal chart entry")
    natal_save.add_argument("natal_id")
    natal_save.add_argument("--utc", required=True, help="Birth time (UTC ISO-8601)")
    natal_save.add_argument("--lat", type=float, required=True, help="Latitude in decimal degrees")
    natal_save.add_argument("--lon", type=float, required=True, help="Longitude in decimal degrees")
    natal_save.add_argument("--name", help="Human-friendly label")
    natal_save.add_argument("--tz", help="IANA timezone identifier for provenance")
    natal_save.add_argument("--place", help="Birth location description")
    natal_save.set_defaults(func=cmd_natal_save)

    natal_delete = natal_sub.add_parser("delete", help="Remove a stored natal chart")
    natal_delete.add_argument("natal_id")
    natal_delete.set_defaults(func=cmd_natal_delete)

    parser._ae_natals_added = True


def cmd_cache_info(_: argparse.Namespace) -> int:
    from .cache.positions_cache import CACHE_DIR, DB as POSITIONS_DB
    import sqlite3

    print(f"cache directory: {CACHE_DIR}")
    if POSITIONS_DB.exists():
        size = POSITIONS_DB.stat().st_size
        row_count = 0
        con = sqlite3.connect(str(POSITIONS_DB))
        try:
            cur = con.execute("SELECT COUNT(*) FROM positions_daily")
            row = cur.fetchone()
            if row:
                row_count = int(row[0])
        except sqlite3.OperationalError:
            row_count = 0
        finally:
            con.close()
        print(f"cache database: {POSITIONS_DB} ({size} bytes, {row_count} rows)")
    else:
        print(f"cache database: {POSITIONS_DB} (missing)")
    return 0


def cmd_cache_warm(args: argparse.Namespace) -> int:
    from .cache.positions_cache import warm_daily

    bodies = (
        [b.strip().lower() for b in args.bodies.split(",") if b.strip()]
        if args.bodies
        else [
            "sun",
            "moon",
            "mercury",
            "venus",
            "mars",
            "jupiter",
            "saturn",
            "uranus",
            "neptune",
            "pluto",
        ]
    )
    if not bodies:
        print("no bodies specified for cache warm", file=sys.stderr)
        return 1

    enable_cache(True)
    start_jd = _iso_to_jd(args.start)
    end_jd = _iso_to_jd(args.end)
    if end_jd < start_jd:
        print("end must be after start", file=sys.stderr)
        return 1

    entries = warm_daily(bodies, start_jd, end_jd)
    print(
        f"warmed {entries} cache entries for bodies {', '.join(bodies)} "
        f"[{args.start} → {args.end}]"
    )
    return 0


def _augment_parser_with_cache(parser: argparse.ArgumentParser) -> None:
    if getattr(parser, "_ae_cache_added", False):
        return
    subparsers = _ensure_subparsers(parser)
    cache = subparsers.add_parser("cache", help="Inspect or warm Swiss ephemeris caches")
    cache_sub = cache.add_subparsers(dest="cache_command")
    cache_sub.required = True

    cache_info = cache_sub.add_parser("info", help="Display cache metadata")
    cache_info.set_defaults(func=cmd_cache_info)

    cache_warm = cache_sub.add_parser("warm", help="Warm the daily positions cache")
    cache_warm.add_argument("--start", required=True, help="Start date (ISO-8601)")
    cache_warm.add_argument("--end", required=True, help="End date (ISO-8601)")
    cache_warm.add_argument(
        "--bodies",
        help="Comma-separated list of bodies (default: Sun, Moon, Mercury … Pluto)",
    )
    cache_warm.set_defaults(func=cmd_cache_warm)

    parser._ae_cache_added = True


def cmd_dataset_parquet(args: argparse.Namespace) -> int:
    if args.input == "-":
        payload_text = sys.stdin.read()
    else:
        payload_text = Path(args.input).read_text(encoding="utf-8")

    try:
        if args.format == "jsonl":
            events = [json.loads(line) for line in payload_text.splitlines() if line.strip()]
        else:
            document = json.loads(payload_text)
            if isinstance(document, dict):
                key = args.key or "events"
                if key not in document:
                    raise KeyError(key)
                events = document[key]
            elif isinstance(document, list):
                events = document
            else:
                raise TypeError("unsupported JSON payload")
        if not isinstance(events, list):
            raise TypeError("event payload must be a list")
    except Exception as exc:  # pragma: no cover - defensive parsing
        print(f"failed to load input events: {exc}", file=sys.stderr)
        return 1

    written = export_parquet_dataset(args.output, events)
    print(f"wrote {written} events to {args.output}")
    return 0


def _augment_parser_with_parquet_dataset(parser: argparse.ArgumentParser) -> None:
    if getattr(parser, "_ae_dataset_added", False):
        return
    subparsers = _ensure_subparsers(parser)
    dataset = subparsers.add_parser("dataset", help="Materialise event datasets")
    dataset_sub = dataset.add_subparsers(dest="dataset_command")
    dataset_sub.required = True

    parquet_cmd = dataset_sub.add_parser("parquet", help="Write canonical events to Parquet")
    parquet_cmd.add_argument("input", help="Input JSON/JSONL file (use '-' for stdin)")
    parquet_cmd.add_argument("output", help="Destination Parquet file or directory")
    parquet_cmd.add_argument(
        "--format",
        choices=("json", "jsonl"),
        default="jsonl",
        help="Input format (default: jsonl)",
    )
    parquet_cmd.add_argument(
        "--key",
        help="JSON key containing events when --format json (default: events)",
    )
    parquet_cmd.set_defaults(func=cmd_dataset_parquet)

    parser._ae_dataset_added = True


def cmd_provision_status(args: argparse.Namespace) -> int:
    meta = get_ephemeris_meta()
    meta["provisioned"] = is_provisioned()
    if args.json:
        _print_json(meta)
    else:
        status = "provisioned" if meta["provisioned"] else "not provisioned"
        print(f"Swiss ephemeris status: {status}")
        if meta.get("swe_version"):
            print(f"pyswisseph version: {meta['swe_version']}")
        if meta.get("ephe_path"):
            print(f"ephemeris path: {meta['ephe_path']}")
    return 0


def cmd_provision_ephemeris(args: argparse.Namespace) -> int:
    meta = provision_ephemeris()
    meta["meta_path"] = str(PROVISION_META)
    if args.json:
        _print_json(meta)
    else:
        print(f"Recorded Swiss ephemeris metadata at {meta['meta_path']}")
        if meta.get("swe_version"):
            print(f"pyswisseph version: {meta['swe_version']}")
        if meta.get("ephe_path"):
            print(f"ephemeris path: {meta['ephe_path']}")
    return 0


def _augment_parser_with_provisioning(parser: argparse.ArgumentParser) -> None:
    if getattr(parser, "_ae_provision_added", False):
        return
    subparsers = _ensure_subparsers(parser)
    provision = subparsers.add_parser("provision", help="Manage Swiss ephemeris provisioning")
    provision_sub = provision.add_subparsers(dest="provision_command")
    provision_sub.required = True

    status = provision_sub.add_parser("status", help="Show provisioning state")
    status.add_argument("--json", action="store_true", help="Emit JSON status information")
    status.set_defaults(func=cmd_provision_status)



def _chart_config_from_args(args: argparse.Namespace) -> ChartConfig:
    """Return a :class:`ChartConfig` built from CLI arguments."""

    zodiac = getattr(args, "zodiac", "tropical")
    ayanamsha = getattr(args, "ayanamsha", None)
    house_system = getattr(args, "house_system", "placidus")
    try:
        return ChartConfig(zodiac=zodiac, ayanamsha=ayanamsha, house_system=house_system)
    except ValueError as exc:
        raise SystemExit(f"Invalid chart configuration: {exc}") from exc



DEFAULT_INGRESS_BODIES = (
    "sun",
    "mercury",
    "venus",
    "mars",
    "jupiter",
    "saturn",
    "uranus",
    "neptune",
    "pluto",
)


def _parse_ingress_bodies(spec: str | None) -> tuple[str, ...]:
    if not spec:
        return tuple(DEFAULT_INGRESS_BODIES)
    parts = [item.strip().lower() for item in spec.split(",") if item.strip()]
    return tuple(parts) if parts else tuple(DEFAULT_INGRESS_BODIES)


def _parse_iso_datetime(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _build_natal_chart_from_args(args: argparse.Namespace):
    natal_iso = getattr(args, "natal_utc", None)
    if not natal_iso:
        return None
    lat = getattr(args, "natal_lat", None)
    lon = getattr(args, "natal_lon", None)
    if lat is None or lon is None:
        return None
    moment = _parse_iso_datetime(natal_iso)
    location = ChartLocation(latitude=float(lat), longitude=float(lon))
    return compute_natal_chart(moment, location)


def _serialize_mundane_chart(chart) -> dict[str, Any]:
    payload = {
        "sign": chart.sign,
        "year": chart.year,
        "event": asdict(chart.event),
        "location": asdict(chart.location) if chart.location else None,
        "positions": {name: pos.to_dict() for name, pos in chart.positions.items()},
        "houses": chart.houses.to_dict() if chart.houses else None,
        "aspects": [asdict(hit) for hit in chart.aspects],
        "natal_aspects": [asdict(hit) for hit in chart.natal_aspects],
    }
    return payload


def _handle_mundane(args: argparse.Namespace):
    has_ingresses = bool(getattr(args, "ingresses", False))
    has_aries = getattr(args, "aries_ingress", None) is not None
    if not (has_ingresses or has_aries):
        return None

    payload: dict[str, Any] = {}
    if has_ingresses:
        if not args.start_utc or not args.end_utc:
            raise SystemExit("--ingresses requires --start-utc and --end-utc")
        start_jd = iso_to_jd(args.start_utc)
        end_jd = iso_to_jd(args.end_utc)
        bodies = _parse_ingress_bodies(getattr(args, "ingress_bodies", None))
        step = float(getattr(args, "ingress_step_hours", 6.0))
        events = find_sign_ingresses(start_jd, end_jd, bodies=bodies, step_hours=step)
        payload["ingresses"] = {
            "parameters": {
                "start_utc": args.start_utc,
                "end_utc": args.end_utc,
                "bodies": list(bodies),
                "step_hours": step,
            },
            "events": [asdict(event) for event in events],
        }

    natal_chart = _build_natal_chart_from_args(args)

    if has_aries:
        year = int(getattr(args, "aries_ingress"))
        location = None
        if args.lat is not None and args.lon is not None:
            location = ChartLocation(latitude=float(args.lat), longitude=float(args.lon))
        quartet = bool(getattr(args, "aries_quartet", False))
        if quartet:
            charts = compute_solar_quartet(
                year,
                location=location,
                natal_chart=natal_chart,
            )
        else:
            charts = [
                compute_solar_ingress_chart(
                    year,
                    "Aries",
                    location=location,
                    natal_chart=natal_chart,
                )
            ]
        payload["aries_ingress"] = {
            "year": year,
            "quartet": quartet,
            "location": asdict(location) if location else None,
            "charts": [_serialize_mundane_chart(chart) for chart in charts],
        }

    return payload

# >>> AUTO-GEN BEGIN: CLI Canonical Export Commands v1.0
from .exporters import write_sqlite_canonical, write_parquet_canonical


def _cli_export(args: argparse.Namespace, events: Sequence[Any]) -> dict[str, int]:
    """Standardized export helper accepting canonical or legacy events."""

    written: dict[str, int] = {}
    if getattr(args, "sqlite", None):
        written["sqlite"] = write_sqlite_canonical(args.sqlite, events)
    if getattr(args, "parquet", None):
        written["parquet"] = write_parquet_canonical(args.parquet, events)
    return written


def _ingress_to_canonical(event: Any) -> dict[str, Any]:
    """Convert an ingress dataclass into a canonical export mapping."""

    payload = {
        "kind": f"ingress_{getattr(event, 'sign', '').lower()}",
        "timestamp": getattr(event, "ts", None) or getattr(event, "timestamp", None),
        "moving": getattr(event, "body", ""),
        "target": getattr(event, "sign", ""),
        "orb_abs": 0.0,
        "orb_allow": 0.0,
        "applying_or_separating": "exact",
        "score": 0.0,
        "lon_moving": getattr(event, "longitude", None),
        "lon_target": None,
        "metadata": {
            "jd": getattr(event, "jd", None),
            "method": getattr(event, "method", "sign_ingress"),
            "sign_index": getattr(event, "sign_index", -1),
        },
    }
    return payload


def add_canonical_export_args(p: argparse.ArgumentParser) -> None:
    group = p.add_argument_group("canonical export")
    group.add_argument("--sqlite", help="Path to SQLite DB; writes into table transits_events")
    group.add_argument(
        "--parquet",
        help="Path to Parquet file or dataset directory",
    )


# >>> AUTO-GEN END: CLI Canonical Export Commands v1.0

# >>> AUTO-GEN BEGIN: cli-run-experimental v1.1
from .detectors import (
    find_eclipses,
    find_lunations,

    find_sign_ingresses,

    find_out_of_bounds,

    find_stations,
    secondary_progressions,
    solar_arc_directions,
    solar_lunar_returns,
)
from .detectors.common import iso_to_jd
from .detectors.common import enable_cache  # ENSURE-LINE
from .cache.positions_cache import warm_daily  # ENSURE-LINE
from .exporters_batch import export_parquet_dataset  # ENSURE-LINE
from .mundane import compute_solar_ingress_chart, compute_solar_quartet
from .chart.natal import ChartLocation, compute_natal_chart


def run_experimental(args) -> None:
    if not any(
        [
            args.eclipses,
            args.lunations,
            args.stations,
            args.returns,
            args.progressions,
            args.directions,
            getattr(args, "oob", False),
        ]
    ):
        return
    chart_config = getattr(args, "chart_config", ChartConfig())
    adapter = SwissEphemerisAdapter.from_chart_config(chart_config)
    start_jd = iso_to_jd(args.start_utc)
    end_jd = iso_to_jd(args.end_utc)
    if args.eclipses:
        ev = find_eclipses(start_jd, end_jd)
        print(f"eclipses: {len(ev)} events")
    if args.lunations:
        ev = find_lunations(start_jd, end_jd)
        print(f"lunations: {len(ev)} events")
    if args.stations:
        ev = find_stations(start_jd, end_jd, None)
        print(f"stations: {len(ev)} events")
    if getattr(args, "oob", False):
        ev = find_out_of_bounds(start_jd, end_jd)
        print(f"out-of-bounds: {len(ev)} events")
    if args.returns:
        if not getattr(args, "natal_utc", None):
            print("returns: missing --natal-utc; skipping")
        else:
            which = getattr(args, "return_kind", "solar")
            ev = solar_lunar_returns(
                iso_to_jd(args.natal_utc), start_jd, end_jd, which, adapter=adapter
            )
            print(f"{which}-returns: {len(ev)} events")
    if args.progressions:
        if not getattr(args, "natal_utc", None):
            print("progressions: missing --natal-utc; skipping")
        else:
            ev = secondary_progressions(
                args.natal_utc, args.start_utc, args.end_utc, config=chart_config
            )
            print(f"progressions: {len(ev)} events")
    if args.directions:
        if not getattr(args, "natal_utc", None):
            print("directions: missing --natal-utc; skipping")
        else:
            ev = solar_arc_directions(
                args.natal_utc, args.start_utc, args.end_utc, config=chart_config
            )
            print(f"solar-arc directions: {len(ev)} events")
# >>> AUTO-GEN END: cli-run-experimental v1.1

__all__ = ["build_parser", "main", "serialize_events_to_json", "json"]


# >>> AUTO-GEN BEGIN: cli-new-detector-flags v1.0
def _augment_parser_with_features(p: argparse.ArgumentParser) -> None:
    targets = getattr(p, "_ae_feature_parsers", [p])
    for target in targets:
        if getattr(target, "_ae_features_added", False):
            continue
        g = target.add_argument_group("Detectors (experimental)")
        g.add_argument("--lunations", action="store_true", help="Enable lunations detector")
        g.add_argument("--eclipses", action="store_true", help="Enable eclipses detector")
        g.add_argument("--oob", action="store_true", help="Enable out-of-bounds detector")
        g.add_argument("--stations", action="store_true", help="Enable stations detector")
        g.add_argument("--progressions", action="store_true", help="Enable secondary progressions")
        g.add_argument("--directions", action="store_true", help="Enable solar arc directions")
        g.add_argument("--returns", action="store_true", help="Enable solar/lunar returns")
        g.add_argument("--profections", action="store_true", help="Enable annual profections")
        g.add_argument("--prog-aspects", action="store_true", help="Enable progressed natal aspects detector")
        g.add_argument("--dir-aspects", action="store_true", help="Enable directed natal aspects detector")
        target._ae_features_added = True
# >>> AUTO-GEN END: cli-new-detector-flags v1.0



def serialize_events_to_json(events: Iterable) -> str:
    """Serialize events into a pretty-printed JSON string."""

    return json.dumps(events_to_dicts(events), indent=2)


def cmd_experimental(args: argparse.Namespace) -> int:
    run_experimental(args)
    return 0


def cmd_env(_: argparse.Namespace) -> int:
    providers = ", ".join(list_providers()) or "(none)"
    print("Registered providers:", providers)
    return 0


def cmd_transits(args: argparse.Namespace) -> int:
    engine_module.FEATURE_LUNATIONS = args.lunations
    engine_module.FEATURE_ECLIPSES = args.eclipses
    engine_module.FEATURE_STATIONS = args.stations
    engine_module.FEATURE_PROGRESSIONS = args.progressions
    engine_module.FEATURE_DIRECTIONS = args.directions
    engine_module.FEATURE_RETURNS = args.returns
    engine_module.FEATURE_PROFECTIONS = args.profections

    include_mirrors = not args.decl_only
    include_aspects = not args.decl_only

    observer = None
    if args.lat is not None and args.lon is not None:
        observer = ObserverLocation(
            latitude_deg=float(args.lat),
            longitude_deg=float(args.lon),
            elevation_m=float(getattr(args, "elevation_m", 0.0) or 0.0),
        )
    if args.topocentric and observer is None:
        print("topocentric mode requires --lat and --lon", file=sys.stderr)
        return 1
    time_scale = TimeScaleContext(ephemeris_scale=args.ephemeris_time_scale.upper())
    ephemeris_config = EphemerisConfig(
        topocentric=bool(args.topocentric),
        observer=observer,
        sidereal=bool(args.sidereal),
        time_scale=time_scale,
    )

    events = scan_contacts(
        start_iso=args.start,
        end_iso=args.end,
        moving=args.moving,
        target=args.target,
        provider_name=args.provider,
        ephemeris_config=ephemeris_config,
        decl_parallel_orb=args.decl_orb,
        decl_contra_orb=args.decl_orb,
        antiscia_orb=args.mirror_orb,
        contra_antiscia_orb=args.mirror_orb,
        step_minutes=args.step,
        aspects_policy_path=args.aspects_policy,

        chart_config=getattr(args, "chart_config", None),

        profile_id=args.profile,
        include_declination=True,
        include_mirrors=include_mirrors,
        include_aspects=include_aspects,
        antiscia_axis=args.mirror_axis,

    )

    if args.json:
        payload = {
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "parameters": {
                "start_timestamp": args.start,
                "end_timestamp": args.end,
                "moving": args.moving,
                "target": args.target,
                "provider": args.provider,
                "target_longitude": args.target_longitude,
            },
            "events": events_to_dicts(events),
        }
        Path(args.json).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Wrote {len(events)} events to {args.json}")

    written = _cli_export(args, events)
    if args.sqlite and written.get("sqlite"):
        print(f"SQLite export complete: {args.sqlite} ({written['sqlite']} rows)")
    if args.parquet and written.get("parquet"):
        print(f"Parquet export complete: {args.parquet} ({written['parquet']} rows)")

    if getattr(args, "narrative", False):
        summary = summarize_top_events(events, top_n=getattr(args, "narrative_top", 5))
        print(summary)

    if not any((args.json, args.sqlite, args.parquet)):
        print(serialize_events_to_json(events))

    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    payload_path = Path(args.path)
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    try:
        validate_payload(args.schema, payload)
    except SchemaValidationError as exc:
        print("Validation failed:", file=sys.stderr)
        for message in exc.errors:
            print("  -", message, file=sys.stderr)
        return 1

    print(f"Payload validated against {args.schema}")
    return 0


def cmd_ingresses(args: argparse.Namespace) -> int:
    chart_config = _chart_config_from_args(args)
    adapter = SwissEphemerisAdapter(chart_config=chart_config)
    start_dt = datetime.fromisoformat(args.start.replace("Z", "+00:00")).astimezone(timezone.utc)
    end_dt = datetime.fromisoformat(args.end.replace("Z", "+00:00")).astimezone(timezone.utc)
    if end_dt <= start_dt:
        print("ingresses: end must be after start", file=sys.stderr)
        return 1
    start_jd = adapter.julian_day(start_dt)
    end_jd = adapter.julian_day(end_dt)
    bodies = [body.strip() for body in args.bodies.split(",") if body.strip()]
    if not bodies:
        bodies = ["Sun"]
    events = find_ingresses(start_jd, end_jd, bodies, step_hours=args.step_hours)
    canonical = [_ingress_to_canonical(event) for event in events]

    if args.json:
        payload = {
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "parameters": {
                "start_timestamp": args.start,
                "end_timestamp": args.end,
                "bodies": bodies,
                "step_hours": args.step_hours,
                "zodiac": chart_config.zodiac,
                "ayanamsha": chart_config.ayanamsha,
                "house_system": chart_config.house_system,
            },
            "events": canonical,
        }
        Path(args.json).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Wrote {len(events)} ingresses to {args.json}")

    written = _cli_export(args, canonical)
    if args.sqlite and written.get("sqlite"):
        print(f"SQLite export complete: {args.sqlite} ({written['sqlite']} rows)")
    if args.parquet and written.get("parquet"):
        print(f"Parquet export complete: {args.parquet} ({written['parquet']} rows)")

    if not any((args.json, args.sqlite, args.parquet)):
        print(json.dumps(canonical, indent=2))

    return 0


def cmd_timelords(args: argparse.Namespace) -> int:
    start_dt = datetime.fromisoformat(args.start.replace("Z", "+00:00")).astimezone(timezone.utc)
    results: list[dict[str, Any]] = []

    if args.vimshottari:
        if args.moon_longitude is None:
            print("timelords: --moon-longitude is required for Vimshottari dashas", file=sys.stderr)
            return 1
        levels = [level.strip() for level in args.timelord_levels.split(",") if level.strip()]
        periods = compute_vimshottari_dasha(
            args.moon_longitude,
            start_dt,
            cycles=args.dasha_cycles,
            levels=tuple(levels) if levels else ("maha", "antar"),
        )
        results.extend(asdict(event) for event in periods)

    if args.zr:
        if args.fortune_longitude is None:
            print("timelords: --fortune-longitude is required for zodiacal releasing", file=sys.stderr)
            return 1
        zr_levels = [level.strip() for level in args.zr_levels.split(",") if level.strip()]
        zr_periods = compute_zodiacal_releasing(
            args.fortune_longitude,
            start_dt,
            lot=args.lot,
            periods=args.zr_periods,
            levels=tuple(zr_levels) if zr_levels else ("l1", "l2"),
        )
        results.extend(asdict(event) for event in zr_periods)

    if not results:
        print("timelords: no systems selected", file=sys.stderr)
        return 1

    payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "start": args.start,
        "events": results,
    }

    if args.json:
        Path(args.json).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Wrote {len(results)} periods to {args.json}")
    else:
        print(json.dumps(payload, indent=2))

    return 0


def _iso_to_jd(iso_ts: str) -> float:
    dt = datetime.fromisoformat(iso_ts.replace('Z', '+00:00')).astimezone(timezone.utc)
    return (dt.timestamp() / 86400.0) + UNIX_EPOCH_JD


def run_experimental(args) -> None:
    # Expect args.start_utc, args.end_utc in ISO-8601, and feature flags
    if not any([args.lunations, args.stations, args.returns]):
        return
    if not args.start_utc or not args.end_utc:
        print("experimental detectors require --start-utc and --end-utc; skipping")
        return
    chart_config = getattr(args, "chart_config", ChartConfig())
    adapter = SwissEphemerisAdapter.from_chart_config(chart_config)
    start_jd = _iso_to_jd(args.start_utc)
    end_jd = _iso_to_jd(args.end_utc)
    if args.lunations:
        ev = find_lunations(start_jd, end_jd)
        print(f"lunations: {len(ev)} events")
    if args.stations:
        ev = find_stations(start_jd, end_jd, None)
        print(f"stations: {len(ev)} events")
    if args.returns:
        # need args.natal_utc and args.return_kind
        if not getattr(args, 'natal_utc', None):
            print("returns: missing --natal-utc; skipping")
        else:
            natal_jd = _iso_to_jd(args.natal_utc)
            which = getattr(args, 'return_kind', 'solar')
            ev = solar_lunar_returns(natal_jd, start_jd, end_jd, which, adapter=adapter)
            print(f"{which}-returns: {len(ev)} events")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="astroengine", description="AstroEngine CLI")
    parser.add_argument(
        "--zodiac",
        choices=sorted(VALID_ZODIAC_SYSTEMS),
        default="tropical",
        help="Zodiac mode for chart and transit computations",
    )
    parser.add_argument(
        "--ayanamsha",
        choices=sorted(SUPPORTED_AYANAMSHAS),
        help=f"Sidereal ayanamsha (required when --zodiac sidereal; default is '{DEFAULT_SIDEREAL_AYANAMSHA}')",
    )
    parser.add_argument("--start-utc", help="Start timestamp (ISO-8601) for experimental detectors")  # ENSURE-LINE
    parser.add_argument("--end-utc", help="End timestamp (ISO-8601) for experimental detectors")  # ENSURE-LINE
    parser.add_argument("--natal-utc", help="Natal timestamp (ISO-8601) for return calculations")  # ENSURE-LINE
    parser.add_argument("--natal-id", help="Natal identifier for provenance and vault operations")  # ENSURE-LINE
    parser.add_argument("--return-kind", default="solar", help="Return kind: solar or lunar")  # ENSURE-LINE
    parser.add_argument("--natal-lat", type=float, help="Latitude for natal chart when computing mundane aspects")
    parser.add_argument("--natal-lon", type=float, help="Longitude for natal chart when computing mundane aspects")
    parser.add_argument("--export-sqlite", help="Write precomputed events to this SQLite file")
    parser.add_argument("--export-parquet", help="Write precomputed events to this Parquet file")
    parser.add_argument("--export-ics", help="Write precomputed events to this ICS calendar file")
    parser.add_argument("--ics-title", default="AstroEngine Events", help="Title to use for ICS export events")
    parser.add_argument("--profile", help="Profile identifier to annotate export metadata")
    parser.add_argument("--lat", type=float, help="Latitude for location-sensitive detectors")
    parser.add_argument("--lon", type=float, help="Longitude for location-sensitive detectors")

    parser.add_argument("--ingresses", action="store_true", help="Emit sign ingress events between --start-utc and --end-utc")
    parser.add_argument("--ingress-bodies", help="Comma-separated list of bodies for ingress detection")
    parser.add_argument(
        "--ingress-step-hours",
        type=float,
        default=6.0,
        help="Sampling cadence in hours for ingress detection",
    )
    parser.add_argument("--aries-ingress", type=int, help="Generate Aries ingress chart for the given year")
    parser.add_argument(
        "--aries-quartet",
        action="store_true",
        help="Include solstice/equinox quartet when computing Aries ingress charts",
    )
    parser.add_argument("--mundane-json", help="Write ingress/chart payloads to this JSON path")

    parser.add_argument(
        "--elevation-m",
        type=float,
        default=0.0,
        help="Observer elevation in meters for topocentric calculations",
    )
    parser.add_argument(
        "--topocentric",
        action="store_true",
        help="Use topocentric coordinates (requires --lat and --lon; refraction disabled)",
    )
    parser.add_argument(
        "--ephemeris-time-scale",
        choices=["tt", "ut"],
        default="tt",
        help="Ephemeris time scale (inputs are always treated as UTC)",
    )
    parser.add_argument(
        "--sidereal",
        action="store_true",
        help="Enable sidereal zodiac output (ayanamsha configuration handled separately)",
    )

    parser.add_argument("--aspects", help="Comma-separated aspect angles for natal aspect detectors")
    parser.add_argument("--orb", type=float, help="Orb allowance in degrees for natal aspect detectors")
    parser.add_argument(
        "--zodiac",
        choices=sorted(VALID_ZODIAC_SYSTEMS),
        default="tropical",
        help="Zodiac frame for calculations (tropical or sidereal)",
    )
    parser.add_argument(
        "--ayanamsha",
        help="Sidereal ayanamsha name when --zodiac=sidereal",
    )
    parser.add_argument(
        "--house-system",
        choices=sorted(VALID_HOUSE_SYSTEMS),
        default="placidus",
        help="Preferred house system for derived charts",
    )
    parser.add_argument("--lunations", action="store_true", help="Run lunation detector")
    parser.add_argument("--eclipses", action="store_true", help="Run eclipse detector")
    parser.add_argument("--stations", action="store_true", help="Run planetary station detector")
    parser.add_argument("--progressions", action="store_true", help="Run secondary progression detector")
    parser.add_argument("--directions", action="store_true", help="Run solar arc direction detector")
    parser.add_argument("--returns", action="store_true", help="Run solar/lunar return detector")
    parser.add_argument("--profections", action="store_true", help="Run annual profection timelord detector")
    parser.add_argument("--prog-aspects", action="store_true", help="Run progressed natal aspect detector")
    parser.add_argument("--dir-aspects", action="store_true", help="Run directed natal aspect detector")
    sub = parser.add_subparsers(dest="command")
    parser._ae_subparsers = sub

    env_parser = sub.add_parser("env", help="List registered providers")
    env_parser.set_defaults(func=cmd_env)

    transits = sub.add_parser("transits", help="Scan for transit contacts")
    feature_targets = getattr(parser, "_ae_feature_parsers", [])
    feature_targets.append(transits)
    parser._ae_feature_parsers = feature_targets
    transits.add_argument("--start", required=True)
    transits.add_argument("--end", required=True)
    transits.add_argument("--moving", default="sun")
    transits.add_argument("--target", default="moon")
    transits.add_argument("--provider", default="swiss")
    transits.add_argument(
        "--decl-orb",
        type=float,
        default=None,
        help="Override declination orb (degrees); defaults to profile policy",
    )
    transits.add_argument(
        "--mirror-orb",
        type=float,
        default=None,
        help="Override antiscia orb (degrees); defaults to profile policy",
    )
    transits.add_argument(
        "--mirror-axis",
        choices=available_antiscia_axes(),
        help="Antiscia axis (profile default when omitted)",
    )
    transits.add_argument(
        "--decl-only",
        action="store_true",
        help="Emit only declination contacts (skip aspects and antiscia)",
    )
    transits.add_argument("--step", type=int, default=60)
    transits.add_argument("--aspects-policy")
    transits.add_argument("--target-longitude", type=float, default=None)
    transits.add_argument("--json")
    transits.add_argument("--narrative", action="store_true", help="Summarize detected contacts")
    transits.add_argument(
        "--narrative-top",
        type=int,
        default=5,
        help="Number of top-scoring events to include in the narrative summary",
    )
    add_canonical_export_args(transits)
    transits.set_defaults(func=cmd_transits)

    experimental = sub.add_parser("experimental", help="Run experimental detectors")
    experimental.add_argument("--start-utc", required=True)
    experimental.add_argument("--end-utc", required=True)
    experimental.add_argument("--natal-utc")
    experimental.add_argument("--return-kind", default="solar")
    experimental.add_argument("--lunations", action="store_true")
    experimental.add_argument("--stations", action="store_true")
    experimental.add_argument("--returns", action="store_true")
    experimental.add_argument("--progressions", action="store_true")  # ENSURE-LINE
    experimental.add_argument("--directions", action="store_true")  # ENSURE-LINE
    experimental.set_defaults(func=cmd_experimental)

    validate = sub.add_parser("validate", help="Validate a JSON payload against a schema")
    validate.add_argument("schema", choices=list(available_schema_keys("jsonschema")))
    validate.add_argument("path")
    validate.set_defaults(func=cmd_validate)


    ingresses = sub.add_parser("ingresses", help="Detect sign ingress events")
    ingresses.add_argument("--start", required=True)
    ingresses.add_argument("--end", required=True)
    ingresses.add_argument("--bodies", default="Sun")
    ingresses.add_argument("--step-hours", type=float, default=6.0)
    ingresses.add_argument("--json")
    add_canonical_export_args(ingresses)
    ingresses.set_defaults(func=cmd_ingresses)

    timelords = sub.add_parser("timelords", help="Compute timelord periods")
    timelords.add_argument("--start", required=True)
    timelords.add_argument("--vimshottari", action="store_true")
    timelords.add_argument("--moon-longitude", type=float)
    timelords.add_argument("--dasha-cycles", type=int, default=1)
    timelords.add_argument(
        "--timelord-levels",
        default="maha,antar",
        help="Comma-separated Vimshottari levels to compute",
    )
    timelords.add_argument("--zr", action="store_true")
    timelords.add_argument("--fortune-longitude", type=float)
    timelords.add_argument("--zr-periods", type=int, default=12)
    timelords.add_argument(
        "--zr-levels",
        default="l1,l2",
        help="Comma-separated releasing levels",
    )
    timelords.add_argument("--lot", default="fortune")
    timelords.add_argument("--json")
    timelords.set_defaults(func=cmd_timelords)


    _augment_parser_with_features(parser)
    setup_plugins(parser)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    _augment_parser_with_natals(parser)
    _augment_parser_with_cache(parser)
    _augment_parser_with_parquet_dataset(parser)
    _augment_parser_with_provisioning(parser)
    _augment_parser_with_features(parser)
    namespace = parser.parse_args(list(argv) if argv is not None else None)


    mundane_payload = _handle_mundane(namespace)
    if mundane_payload is not None:
        output_path = getattr(namespace, "mundane_json", None)
        payload_json = json.dumps(mundane_payload, indent=2)
        if output_path:
            Path(output_path).write_text(payload_json, encoding="utf-8")
            print(f"Wrote mundane payload to {output_path}")
        else:
            print(payload_json)
        return 0

    zodiac = namespace.zodiac
    ayanamsha = namespace.ayanamsha
    if zodiac == "sidereal" and ayanamsha is None:
        ayanamsha = DEFAULT_SIDEREAL_AYANAMSHA
    if zodiac != "sidereal":
        ayanamsha = None

    chart_config = ChartConfig(zodiac=zodiac, ayanamsha=ayanamsha)
    SwissEphemerisAdapter.configure_defaults(chart_config=chart_config)
    namespace.chart_config = chart_config
    namespace.ayanamsha = chart_config.ayanamsha


    run_experimental(namespace)
    func = getattr(namespace, "func", None)
    if func is not None:
        return func(namespace)
    if not any((namespace.lunations, namespace.stations, namespace.returns)):
        parser.print_help()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
