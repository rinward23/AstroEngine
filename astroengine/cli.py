"""Command line interface for AstroEngine."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, List, Sequence


from . import engine as engine_module
from .app_api import canonicalize_events, run_scan_or_raise
from .engine import events_to_dicts, scan_contacts
from .pipeline.provision import provision_ephemeris, is_provisioned  # ENSURE-LINE
from .providers import list_providers
from .exporters_ics import write_ics_canonical
from .validation import (
    SchemaValidationError,
    available_schema_keys,
    validate_payload,
)
from .userdata.vault import Natal, save_natal, load_natal, list_natals, delete_natal  # ENSURE-LINE
from .utils import (
    DEFAULT_TARGET_FRAMES,
    DEFAULT_TARGET_SELECTION,
    DETECTOR_NAMES,
    ENGINE_FLAG_MAP,
    available_frames,
    expand_targets,
)


def _augment_parser_with_natals(parser: argparse.ArgumentParser) -> None:
    """Placeholder for natal vault wiring in lightweight builds."""

    return None


def _augment_parser_with_cache(parser: argparse.ArgumentParser) -> None:
    """Placeholder for cache warmers in lightweight builds."""

    return None


def _augment_parser_with_parquet_dataset(parser: argparse.ArgumentParser) -> None:
    """Placeholder for parquet dataset integration in lightweight builds."""

    return None


def _augment_parser_with_provisioning(parser: argparse.ArgumentParser) -> None:
    """Placeholder for ephemeris provisioning hooks in lightweight builds."""

    return None

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
    find_lunations,
    find_stations,
    secondary_progressions,
    solar_arc_directions,
    solar_lunar_returns,
)
from .detectors.common import iso_to_jd
from .detectors.common import enable_cache  # ENSURE-LINE
from .cache.positions_cache import warm_daily  # ENSURE-LINE
from .exporters_batch import export_parquet_dataset  # ENSURE-LINE


def run_experimental(args) -> None:
    if not any(
        [
            args.lunations,
            args.stations,
            args.returns,
            args.progressions,
            args.directions,
        ]
    ):
        return
    start_jd = iso_to_jd(args.start_utc)
    end_jd = iso_to_jd(args.end_utc)
    if args.lunations:
        ev = find_lunations(start_jd, end_jd)
        print(f"lunations: {len(ev)} events")
    if args.stations:
        ev = find_stations(start_jd, end_jd, None)
        print(f"stations: {len(ev)} events")
    if args.returns:
        if not getattr(args, "natal_utc", None):
            print("returns: missing --natal-utc; skipping")
        else:
            which = getattr(args, "return_kind", "solar")
            ev = solar_lunar_returns(iso_to_jd(args.natal_utc), start_jd, end_jd, which)
            print(f"{which}-returns: {len(ev)} events")
    if args.progressions:
        if not getattr(args, "natal_utc", None):
            print("progressions: missing --natal-utc; skipping")
        else:
            ev = secondary_progressions(args.natal_utc, args.start_utc, args.end_utc)
            print(f"progressions: {len(ev)} events")
    if args.directions:
        if not getattr(args, "natal_utc", None):
            print("directions: missing --natal-utc; skipping")
        else:
            ev = solar_arc_directions(args.natal_utc, args.start_utc, args.end_utc)
            print(f"solar-arc directions: {len(ev)} events")
# >>> AUTO-GEN END: cli-run-experimental v1.1

__all__ = ["build_parser", "main", "serialize_events_to_json", "json"]


# >>> AUTO-GEN BEGIN: cli-natal-stub v1.0
def _augment_parser_with_natals(parser: argparse.ArgumentParser) -> None:
    """Placeholder for natal vault integration (no-op until implemented)."""

    return None


# >>> AUTO-GEN END: cli-natal-stub v1.0


# >>> AUTO-GEN BEGIN: cli-cache-stub v1.0
def _augment_parser_with_cache(parser: argparse.ArgumentParser) -> None:
    """Placeholder for cache warmers/controls (currently unused)."""

    return None


# >>> AUTO-GEN END: cli-cache-stub v1.0

# >>> AUTO-GEN BEGIN: cli-parquet-stub v1.0
def _augment_parser_with_parquet_dataset(parser: argparse.ArgumentParser) -> None:
    """Placeholder for batch-parquet export commands."""

    return None


# >>> AUTO-GEN END: cli-parquet-stub v1.0

# >>> AUTO-GEN BEGIN: cli-provision-stub v1.0
def _augment_parser_with_provisioning(parser: argparse.ArgumentParser) -> None:
    """Placeholder for provisioning helpers (Swiss downloads etc.)."""

    return None


# >>> AUTO-GEN END: cli-provision-stub v1.0

# >>> AUTO-GEN BEGIN: cli-new-detector-flags v1.0
def _augment_parser_with_features(p: argparse.ArgumentParser) -> None:
    targets = getattr(p, "_ae_feature_parsers", [p])
    for target in targets:
        if getattr(target, "_ae_features_added", False):
            continue
        g = target.add_argument_group("Detectors (experimental)")
        g.add_argument("--lunations", action="store_true", help="Enable lunations detector")
        g.add_argument("--eclipses", action="store_true", help="Enable eclipses detector")
        g.add_argument("--stations", action="store_true", help="Enable stations detector")
        g.add_argument("--progressions", action="store_true", help="Enable secondary progressions")
        g.add_argument("--directions", action="store_true", help="Enable solar arc directions")
        g.add_argument("--returns", action="store_true", help="Enable solar/lunar returns")
        g.add_argument("--profections", action="store_true", help="Enable annual profections")
        g.add_argument("--prog-aspects", action="store_true", help="Enable progressed natal aspects detector")
        g.add_argument("--dir-aspects", action="store_true", help="Enable directed natal aspects detector")
        target._ae_features_added = True
# >>> AUTO-GEN END: cli-new-detector-flags v1.0



DEFAULT_MOVING_BODIES = ["Sun", "Mars", "Jupiter"]


def _normalize_detectors(values: Iterable[str] | None) -> List[str]:
    if not values:
        return []
    selected: set[str] = set()
    for item in values:
        if not item:
            continue
        raw = str(item)
        for token in raw.replace(",", " ").split():
            key = token.strip().lower()
            if not key:
                continue
            if key == "all":
                return sorted(DETECTOR_NAMES)
            if key in DETECTOR_NAMES:
                selected.add(key)
    return sorted(selected)


def _set_engine_detector_flags(detectors: Iterable[str]) -> None:
    active = {name.lower() for name in detectors}
    for name, attr in ENGINE_FLAG_MAP.items():
        setattr(engine_module, attr, name in active)


def _event_summary(event: Any) -> dict[str, Any]:
    if isinstance(event, dict):
        data = event
    elif is_dataclass(event):
        data = asdict(event)
    elif hasattr(event, "model_dump"):
        try:
            dumped = event.model_dump()
        except Exception:  # pragma: no cover - defensive
            dumped = None
        data = dumped if isinstance(dumped, dict) else {}
    elif hasattr(event, "__dict__"):
        data = dict(vars(event))
    else:
        data = {}
    ts = data.get("ts") or data.get("timestamp") or data.get("when_iso")
    moving = data.get("moving") or data.get("body")
    aspect = data.get("aspect") or data.get("kind")
    target = data.get("target") or data.get("natal")
    orb = data.get("orb")
    if orb is None:
        orb = data.get("orb_abs")
    score = data.get("score") or data.get("severity")
    return {
        "ts": ts,
        "moving": moving,
        "aspect": aspect,
        "target": target,
        "orb": orb,
        "score": score,
    }


def _format_event_table(events: Iterable[Any]) -> str:
    rows = []
    for event in events:
        summary = _event_summary(event)
        if not summary.get("ts"):
            continue
        rows.append(summary)
    rows.sort(key=lambda item: str(item.get("ts")))
    if not rows:
        return ""
    headers = ["Timestamp", "Moving", "Aspect", "Target", "Orb", "Score"]
    table_rows: List[List[str]] = []
    for row in rows:
        orb = row.get("orb")
        score = row.get("score")
        table_rows.append(
            [
                str(row.get("ts", "")),
                str(row.get("moving", "")),
                str(row.get("aspect", "")),
                str(row.get("target", "")),
                "" if orb is None else f"{float(orb):+0.2f}",
                "" if score is None else f"{float(score):0.2f}",
            ]
        )
    widths = [len(h) for h in headers]
    for row in table_rows:
        for idx, value in enumerate(row):
            widths[idx] = max(widths[idx], len(value))
    header_line = " | ".join(h.ljust(widths[idx]) for idx, h in enumerate(headers))
    divider = "-+-".join("-" * widths[idx] for idx in range(len(headers)))
    body_lines = [" | ".join(value.ljust(widths[idx]) for idx, value in enumerate(row)) for row in table_rows]
    return "\n".join([header_line, divider, *body_lines])


def _canonical_events_to_dicts(events: Iterable[Any]) -> List[dict[str, Any]]:
    payload: List[dict[str, Any]] = []
    for event in events:
        if isinstance(event, dict):
            payload.append(dict(event))
            continue
        if is_dataclass(event):
            payload.append(asdict(event))
            continue
        if hasattr(event, "model_dump"):
            try:
                dumped = event.model_dump()
            except Exception:  # pragma: no cover - defensive
                dumped = None
            if isinstance(dumped, dict):
                payload.append(dumped)
                continue
        if hasattr(event, "__dict__"):
            payload.append(dict(vars(event)))
            continue
        payload.append({"value": repr(event)})
    return payload


def _resolve_targets_cli(
    raw_targets: Iterable[str] | None,
    frames: Iterable[str] | None,
) -> List[str]:
    cleaned = [token.strip() for token in (raw_targets or []) if token]
    if not cleaned:
        return expand_targets(frames or DEFAULT_TARGET_FRAMES, DEFAULT_TARGET_SELECTION)
    return expand_targets(frames or DEFAULT_TARGET_FRAMES, cleaned)


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
    events = scan_contacts(
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

    if not any((args.json, args.sqlite, args.parquet)):
        print(serialize_events_to_json(events))

    return 0


def cmd_scan(args: argparse.Namespace) -> int:
    detectors = _normalize_detectors(getattr(args, "detectors", None))
    _set_engine_detector_flags(detectors)

    moving = list(dict.fromkeys(args.moving or DEFAULT_MOVING_BODIES))
    frame_selection = list(dict.fromkeys(args.target_frames or [])) or list(DEFAULT_TARGET_FRAMES)
    targets = _resolve_targets_cli(args.targets, frame_selection)

    entrypoints: List[str] = []
    for raw in getattr(args, "entrypoint", []) or []:
        token = str(raw).strip()
        if token:
            entrypoints.append(token)

    if getattr(args, "cache", False):
        enable_cache(True)

    provider = args.provider
    if provider == "auto":
        provider = None

    try:
        result = run_scan_or_raise(
            start_utc=args.start_utc,
            end_utc=args.end_utc,
            moving=moving,
            targets=targets,
            provider=provider,
            profile_id=args.profile,
            step_minutes=args.step_minutes,
            detectors=detectors,
            target_frames=frame_selection,
            sidereal=args.sidereal if args.sidereal is not None else None,
            ayanamsha=args.ayanamsha or None,
            entrypoints=entrypoints or None,
            return_used_entrypoint=True,
        )
    except RuntimeError as exc:  # pragma: no cover - exercised in integration tests
        print(f"Scan failed: {exc}", file=sys.stderr)
        return 1

    raw_events, used_entrypoint = result
    canonical_events = canonicalize_events(raw_events)
    records = _canonical_events_to_dicts(canonical_events)

    if args.export_json:
        try:
            path = Path(args.export_json)
            path.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"JSON export complete: {path} ({len(records)} events)")
        except Exception as exc:
            print(f"JSON export failed ({exc})", file=sys.stderr)

    if args.export_sqlite:
        try:
            rows = write_sqlite_canonical(args.export_sqlite, canonical_events)
            print(f"SQLite export complete: {args.export_sqlite} ({rows} rows)")
        except Exception as exc:
            print(f"SQLite export failed ({exc})", file=sys.stderr)

    if args.export_parquet:
        try:
            rows = write_parquet_canonical(args.export_parquet, canonical_events)
            print(f"Parquet export complete: {args.export_parquet} ({rows} rows)")
        except Exception as exc:
            print(f"Parquet export failed ({exc})", file=sys.stderr)

    if args.export_ics:
        try:
            rows = write_ics_canonical(
                args.export_ics,
                canonical_events,
                calendar_name=args.ics_title or "AstroEngine Events",
            )
            print(f"ICS export complete: {args.export_ics} ({rows} events)")
        except Exception as exc:
            print(f"ICS export failed ({exc})", file=sys.stderr)

    table = _format_event_table(canonical_events)
    module_name, func_name = used_entrypoint
    print(f"Scan entrypoint: {module_name}.{func_name}")
    print(f"Detected {len(canonical_events)} events")
    if detectors:
        print("Detectors:", ", ".join(detectors))
    if table:
        print(table)
    elif not canonical_events:
        print("No events detected for the provided window.")

    if not any(
        [
            args.export_json,
            args.export_sqlite,
            args.export_parquet,
            args.export_ics,
        ]
    ):
        print(json.dumps(records, indent=2, ensure_ascii=False))

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
            ev = solar_lunar_returns(natal_jd, start_jd, end_jd, which)
            print(f"{which}-returns: {len(ev)} events")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="astroengine", description="AstroEngine CLI")
    parser.add_argument("--start-utc", help="Start timestamp (ISO-8601) for experimental detectors")  # ENSURE-LINE
    parser.add_argument("--end-utc", help="End timestamp (ISO-8601) for experimental detectors")  # ENSURE-LINE
    parser.add_argument("--natal-utc", help="Natal timestamp (ISO-8601) for return calculations")  # ENSURE-LINE
    parser.add_argument("--natal-id", help="Natal identifier for provenance and vault operations")  # ENSURE-LINE
    parser.add_argument("--return-kind", default="solar", help="Return kind: solar or lunar")  # ENSURE-LINE
    parser.add_argument("--profile", help="Profile identifier to annotate export metadata")
    parser.add_argument("--lat", type=float, help="Latitude for location-sensitive detectors")
    parser.add_argument("--lon", type=float, help="Longitude for location-sensitive detectors")
    parser.add_argument("--aspects", help="Comma-separated aspect angles for natal aspect detectors")
    parser.add_argument("--orb", type=float, help="Orb allowance in degrees for natal aspect detectors")
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

    env_parser = sub.add_parser("env", help="List registered providers")
    env_parser.set_defaults(func=cmd_env)

    scan = sub.add_parser("scan", help="Run a canonical transit scan with presets")
    scan.add_argument("--start-utc", required=True, help="Window start timestamp (ISO-8601)")
    scan.add_argument("--end-utc", required=True, help="Window end timestamp (ISO-8601)")
    scan.add_argument(
        "--provider",
        default="auto",
        help="Ephemeris provider (auto, swiss, pymeeus, skyfield)",
    )
    scan.add_argument(
        "--moving",
        nargs="+",
        default=DEFAULT_MOVING_BODIES,
        help="Transiting bodies to track (default: %(default)s)",
    )
    scan.add_argument(
        "--targets",
        nargs="+",
        help="Target bodies or qualified symbols (e.g. natal:Sun)",
    )
    scan.add_argument(
        "--target-frame",
        "--frame",
        dest="target_frames",
        action="append",
        choices=available_frames(),
        help="Target frame to prefix targets (repeatable)",
    )
    scan.add_argument(
        "--detector",
        "--detectors",
        dest="detectors",
        action="append",
        choices=sorted(DETECTOR_NAMES),
        help="Enable optional detectors (repeatable, use 'all' for every toggle)",
    )
    scan.add_argument(
        "--entrypoint",
        action="append",
        help="Explicit scan entrypoint module:function (repeatable)",
    )
    scan.add_argument(
        "--step-minutes",
        type=int,
        default=60,
        help="Sampling cadence in minutes (default: %(default)s)",
    )
    scan.add_argument("--export-json", help="Write canonical events to a JSON file")
    scan.add_argument("--export-sqlite", help="Write canonical events to a SQLite file")
    scan.add_argument("--export-parquet", help="Write canonical events to a Parquet dataset")
    scan.add_argument("--export-ics", help="Write canonical events to an ICS calendar file")
    scan.add_argument(
        "--ics-title",
        default="AstroEngine Events",
        help="Calendar title to embed when exporting ICS",
    )
    scan.add_argument(
        "--cache",
        action="store_true",
        help="Enable Swiss longitude caching when available",
    )
    scan.add_argument(
        "--sidereal",
        dest="sidereal",
        action="store_true",
        help="Use sidereal zodiac settings for this scan",
    )
    scan.add_argument(
        "--tropical",
        dest="sidereal",
        action="store_false",
        help="Force tropical zodiac for this scan",
    )
    scan.set_defaults(sidereal=None)
    scan.add_argument("--ayanamsha", help="Sidereal ayanāṁśa to apply when sidereal is enabled")
    scan.set_defaults(func=cmd_scan)

    transits = sub.add_parser("transits", help="Scan for transit contacts")
    feature_targets = getattr(parser, "_ae_feature_parsers", [])
    feature_targets.append(transits)
    parser._ae_feature_parsers = feature_targets
    transits.add_argument("--start", required=True)
    transits.add_argument("--end", required=True)
    transits.add_argument("--moving", default="sun")
    transits.add_argument("--target", default="moon")
    transits.add_argument("--provider", default="swiss")
    transits.add_argument("--decl-orb", type=float, default=0.5)
    transits.add_argument("--mirror-orb", type=float, default=2.0)
    transits.add_argument("--step", type=int, default=60)
    transits.add_argument("--aspects-policy")
    transits.add_argument("--target-longitude", type=float, default=None)
    transits.add_argument("--json")
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

    _augment_parser_with_features(parser)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    _augment_parser_with_features(parser)
    namespace = parser.parse_args(list(argv) if argv is not None else None)

    run_experimental(namespace)
    func = getattr(namespace, "func", None)
    if func is not None:
        return func(namespace)
    if not any((namespace.lunations, namespace.stations, namespace.returns)):
        parser.print_help()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
