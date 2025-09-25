"""Command line interface for AstroEngine."""

# isort: skip_file

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from . import engine as engine_module
from .app_api import canonicalize_events, run_scan_or_raise
from .astro.declination import available_antiscia_axes
from .cache.positions_cache import warm_daily
from .chart import ChartLocation, NatalChart, compute_natal_chart
from .chart.composite import compute_composite_chart
from .chart.config import (
    DEFAULT_SIDEREAL_AYANAMSHA,
    SUPPORTED_AYANAMSHAS,
    VALID_HOUSE_SYSTEMS,
    VALID_ZODIAC_SYSTEMS,
    ChartConfig,
)
from .detectors import (
    find_eclipses,
    find_lunations,
    find_out_of_bounds,
    find_sign_ingresses,
    find_stations,
    secondary_progressions,
    solar_arc_directions,
    solar_lunar_returns,
)
from .detectors.common import enable_cache, iso_to_jd
from .detectors.ingress import find_ingresses
from .engine import TargetFrameResolver, events_to_dicts, scan_contacts
from .ephemeris import (
    EphemerisConfig,
    ObserverLocation,
    SwissEphemerisAdapter,
    TimeScaleContext,
)
from .exporters import write_parquet_canonical, write_sqlite_canonical
from .exporters_batch import export_parquet_dataset
from .exporters_ics import (
    DEFAULT_DESCRIPTION_TEMPLATE as ICS_DEFAULT_DESCRIPTION_TEMPLATE,
)
from .exporters_ics import DEFAULT_SUMMARY_TEMPLATE as ICS_DEFAULT_SUMMARY_TEMPLATE
from .exporters_ics import (
    write_ics,
    write_ics_calendar,
    write_ics_canonical,
)
from .infrastructure.storage.sqlite import SQLiteMigrator
from .infrastructure.storage.sqlite.query import top_events_by_score
from .mundane import compute_solar_ingress_chart, compute_solar_quartet
from .narrative import compose_narrative, summarize_top_events
from .pipeline.provision import PROVISION_META  # ENSURE-LINE
from .pipeline.provision import (
    get_ephemeris_meta,
    is_provisioned,
    provision_ephemeris,
)
from .plugins import ExportContext, get_plugin_manager
from .providers import list_providers
from .timelords import TimelordCalculator, active_timelords
from .timelords.context import build_context
from .timelords.dashas import compute_vimshottari_dasha
from .timelords.zr import compute_zodiacal_releasing
from .userdata.vault import list_natals  # ENSURE-LINE
from .userdata.vault import (
    Natal,
    delete_natal,
    load_natal,
    save_natal,
)
from .utils import (
    DEFAULT_TARGET_FRAMES,
    DEFAULT_TARGET_SELECTION,
    DETECTOR_NAMES,
    ENGINE_FLAG_MAP,
    available_frames,
    expand_targets,
)
from .ux.maps import astrocartography_lines, local_space_vectors
from .ux.plugins import setup_cli as setup_plugins
from .ux.timelines import outer_cycle_windows
from .validation import SchemaValidationError, available_schema_keys, validate_payload


def _ensure_subparsers(parser: argparse.ArgumentParser) -> argparse._SubParsersAction:
    subparsers = getattr(parser, "_ae_subparsers", None)
    if subparsers is None:
        subparsers = parser.add_subparsers(dest="command")
        parser._ae_subparsers = subparsers
    return subparsers


def _print_json(payload: Any) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def cmd_natal_list(_: argparse.Namespace) -> int:
    entries = list_natals()
    if not entries:
        print("No natal charts stored.")
    else:
        print("Stored natal charts:")
        for ident in entries:
            print(f" - {ident}")
    return 0


def cmd_natal_show(args: argparse.Namespace) -> int:
    try:
        natal = load_natal(args.natal_id)
    except FileNotFoundError:
        print(f"natal '{args.natal_id}' not found", file=sys.stderr)
        return 1
    print(json.dumps(asdict(natal), indent=2))
    return 0


def cmd_natal_save(args: argparse.Namespace) -> int:
    entry = Natal(
        natal_id=args.natal_id,
        utc=args.utc,
        lat=float(args.lat),
        lon=float(args.lon),
        name=getattr(args, "name", None),
        tz=getattr(args, "tz", None),
        place=getattr(args, "place", None),
    )
    save_natal(entry)
    print(f"Saved natal '{args.natal_id}'.")
    return 0


def cmd_natal_delete(args: argparse.Namespace) -> int:
    if delete_natal(args.natal_id):
        print(f"Deleted natal '{args.natal_id}'.")
        return 0
    print(f"natal '{args.natal_id}' not found", file=sys.stderr)
    return 1


def _augment_parser_with_natals(parser: argparse.ArgumentParser) -> None:
    if getattr(parser, "_ae_natals_added", False):
        return
    subparsers = _ensure_subparsers(parser)
    natal = subparsers.add_parser("natal", help="Manage the natal vault")
    natal_sub = natal.add_subparsers(dest="natal_command")
    natal_sub.required = True

    natal_list = natal_sub.add_parser(
        "list", help="List stored natal chart identifiers"
    )
    natal_list.set_defaults(func=cmd_natal_list)

    natal_show = natal_sub.add_parser("show", help="Display a stored natal chart")
    natal_show.add_argument("natal_id")
    natal_show.set_defaults(func=cmd_natal_show)

    natal_save = natal_sub.add_parser("save", help="Persist a natal chart entry")
    natal_save.add_argument("natal_id")
    natal_save.add_argument("--utc", required=True, help="Birth time (UTC ISO-8601)")
    natal_save.add_argument(
        "--lat", type=float, required=True, help="Latitude in decimal degrees"
    )
    natal_save.add_argument(
        "--lon", type=float, required=True, help="Longitude in decimal degrees"
    )
    natal_save.add_argument("--name", help="Human-friendly label")
    natal_save.add_argument("--tz", help="IANA timezone identifier for provenance")
    natal_save.add_argument("--place", help="Birth location description")
    natal_save.set_defaults(func=cmd_natal_save)

    natal_delete = natal_sub.add_parser("delete", help="Remove a stored natal chart")
    natal_delete.add_argument("natal_id")
    natal_delete.set_defaults(func=cmd_natal_delete)

    parser._ae_natals_added = True


def cmd_plugins(args: argparse.Namespace) -> int:
    runtime = get_plugin_manager()
    show_all = not any(
        [
            args.entrypoints,
            args.detectors,
            args.score_extensions,
            args.ui_panels,
            args.json,
        ]
    )
    payload: dict[str, Any] = {}
    if args.entrypoints or show_all or args.json:
        payload["entrypoints"] = list(runtime.loaded_entrypoints())
        if not args.json:
            if payload["entrypoints"]:
                print("Loaded entrypoints:")
                for name in payload["entrypoints"]:
                    print(" -", name)
            else:
                print("No plugin entrypoints discovered.")

    if args.detectors or show_all or args.json:
        detector_specs = []
        for spec in runtime.detectors():
            detector_specs.append({"name": spec.name, "metadata": dict(spec.metadata)})
        payload["detectors"] = detector_specs
        if not args.json:
            print("Detectors:")
            if detector_specs:
                for spec in detector_specs:
                    print(f" - {spec['name']}")
            else:
                print(" - none registered")

    if args.score_extensions or show_all or args.json:
        extensions = []
        for spec in runtime.score_extensions().iter_extensions():
            extensions.append({"name": spec.name, "namespace": spec.namespace})
        payload["score_extensions"] = extensions
        if not args.json:
            print("Score extensions:")
            if extensions:
                for spec in extensions:
                    print(f" - {spec['name']} ({spec['namespace']})")
            else:
                print(" - none registered")

    if args.ui_panels or show_all or args.json:
        panels = [panel.as_dict() for panel in runtime.collect_ui_panels()]
        payload["ui_panels"] = panels
        if not args.json:
            print("UI panels:")
            if panels:
                for panel in panels:
                    print(f" - {panel['identifier']}: {panel['component']}")
            else:
                print(" - none registered")

    if args.json:
        print(json.dumps(payload, indent=2))
    return 0


def cmd_cache_info(_: argparse.Namespace) -> int:
    import sqlite3

    from .cache.positions_cache import CACHE_DIR
    from .cache.positions_cache import DB as POSITIONS_DB

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
    start_jd = iso_to_jd(args.start)
    end_jd = iso_to_jd(args.end)
    if end_jd < start_jd:
        print("end must be after start", file=sys.stderr)
        return 1

    entries = warm_daily(bodies, start_jd, end_jd)
    print(
        f"warmed {entries} cache entries for bodies {', '.join(bodies)} "
        f"[{args.start} → {args.end}]"
    )
    return 0


def cmd_ops_migrate(args: argparse.Namespace) -> int:
    migrator = SQLiteMigrator(args.sqlite)
    revision = args.revision or "head"
    try:
        migrator.upgrade(revision)
    except Exception as exc:
        print(f"Migration failed: {exc}", file=sys.stderr)
        return 1
    current = migrator.current()
    print(f"SQLite schema migrated to {current or 'base'}")
    return 0


def _augment_parser_with_cache(parser: argparse.ArgumentParser) -> None:
    if getattr(parser, "_ae_cache_added", False):
        return
    subparsers = _ensure_subparsers(parser)
    cache = subparsers.add_parser(
        "cache", help="Inspect or warm Swiss ephemeris caches"
    )
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
            events = [
                json.loads(line) for line in payload_text.splitlines() if line.strip()
            ]
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

    parquet_cmd = dataset_sub.add_parser(
        "parquet", help="Write canonical events to Parquet"
    )
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
    provision = subparsers.add_parser(
        "provision", help="Manage Swiss ephemeris provisioning"
    )
    provision_sub = provision.add_subparsers(dest="provision_command")
    provision_sub.required = True

    status = provision_sub.add_parser("status", help="Show provisioning state")
    status.add_argument(
        "--json", action="store_true", help="Emit JSON status information"
    )
    status.set_defaults(func=cmd_provision_status)


def _chart_config_from_args(args: argparse.Namespace) -> ChartConfig:
    """Return a :class:`ChartConfig` built from CLI arguments."""

    zodiac = getattr(args, "zodiac", "tropical")
    ayanamsha = getattr(args, "ayanamsha", None)
    house_system = getattr(args, "house_system", "placidus")
    try:
        return ChartConfig(
            zodiac=zodiac, ayanamsha=ayanamsha, house_system=house_system
        )
    except ValueError as exc:
        raise SystemExit(f"Invalid chart configuration: {exc}") from exc


def _parse_iso_arg(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def _primary_chart(args: argparse.Namespace) -> NatalChart | None:
    natal_ts = getattr(args, "natal_utc", None)
    lat = getattr(args, "lat", None)
    lon = getattr(args, "lon", None)
    if not natal_ts or lat is None or lon is None:
        return None
    moment = _parse_iso_arg(str(natal_ts))
    location = ChartLocation(latitude=float(lat), longitude=float(lon))
    return compute_natal_chart(moment, location)


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
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


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


def _partner_chart(args: argparse.Namespace) -> NatalChart | None:
    partner_ts = getattr(args, "partner_utc", None)
    lat = getattr(args, "partner_lat", None)
    lon = getattr(args, "partner_lon", None)
    if not partner_ts or lat is None or lon is None:
        return None
    moment = _parse_iso_arg(str(partner_ts))
    location = ChartLocation(latitude=float(lat), longitude=float(lon))
    return compute_natal_chart(moment, location)


def _resolver_for_target_frame(args: argparse.Namespace) -> TargetFrameResolver | None:
    frame = getattr(args, "target_frame", "natal")
    frame_lower = frame.lower()
    target_name = getattr(args, "target", None)
    static_positions: dict[str, float] = {}
    if target_name and getattr(args, "target_longitude", None) is not None:
        try:
            static_positions[target_name.lower()] = float(args.target_longitude) % 360.0
        except Exception:
            pass

    primary = _primary_chart(args)

    if frame_lower == "natal":
        if primary is None and not static_positions:
            return None
        return TargetFrameResolver(
            "natal", natal_chart=primary, static_positions=static_positions
        )

    if frame_lower == "progressed":
        if primary is None:
            raise ValueError(
                "--target-frame progressed requires --natal-utc, --lat, and --lon"
            )
        return TargetFrameResolver(
            "progressed", natal_chart=primary, static_positions=static_positions
        )

    if frame_lower == "directed":
        if primary is None:
            raise ValueError(
                "--target-frame directed requires --natal-utc, --lat, and --lon"
            )
        return TargetFrameResolver("directed", natal_chart=primary)

    if frame_lower == "composite":
        if primary is None:
            raise ValueError(
                "--target-frame composite requires --natal-utc, --lat, and --lon"
            )
        partner = _partner_chart(args)
        if partner is None:
            raise ValueError(
                "--target-frame composite requires --partner-utc, --partner-lat, and --partner-lon"
            )
        composite = compute_composite_chart(primary, partner)
        return TargetFrameResolver(
            "composite", natal_chart=primary, composite_chart=composite
        )

    raise ValueError(f"Unsupported target frame '{frame}'")


def _serialize_mundane_chart(chart) -> dict[str, Any]:
    payload = {
        "sign": chart.sign,
        "year": chart.year,
        "event": asdict(chart.event),
        "location": asdict(chart.location) if chart.location else None,
        "positions": {
            name: asdict(pos) if is_dataclass(pos) else dict(pos)
            for name, pos in chart.positions.items()
        },
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
        year = int(args.aries_ingress)
        location = None
        if args.lat is not None and args.lon is not None:
            location = ChartLocation(
                latitude=float(args.lat), longitude=float(args.lon)
            )
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


def _cli_export(args: argparse.Namespace, events: Sequence[Any]) -> dict[str, int]:
    """Standardized export helper accepting canonical or legacy events."""

    written: dict[str, int] = {}
    if getattr(args, "sqlite", None):
        written["sqlite"] = write_sqlite_canonical(args.sqlite, events)
    if getattr(args, "parquet", None):

        written["parquet"] = write_parquet_canonical(args.parquet, events)
    runtime = get_plugin_manager()
    runtime.post_export(
        ExportContext(
            destinations=dict(written),
            events=tuple(events),
            arguments=dict(vars(args)),
        )
    )

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
    group.add_argument(
        "--sqlite", help="Path to SQLite DB; writes into table transits_events"
    )
    group.add_argument(
        "--parquet",
        help="Path to Parquet file or dataset directory",
    )
    group.add_argument(
        "--parquet-compression",
        default="snappy",
        help="Compression codec for Parquet exports (snappy, gzip, brotli, ...)",
    )


# >>> AUTO-GEN END: CLI Canonical Export Commands v1.0


# >>> AUTO-GEN BEGIN: cli-run-experimental v1.1
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
        g.add_argument(
            "--lunations", action="store_true", help="Enable lunations detector"
        )
        g.add_argument(
            "--eclipses", action="store_true", help="Enable eclipses detector"
        )
        g.add_argument(
            "--oob", action="store_true", help="Enable out-of-bounds detector"
        )
        g.add_argument(
            "--stations", action="store_true", help="Enable stations detector"
        )
        g.add_argument(
            "--progressions", action="store_true", help="Enable secondary progressions"
        )
        g.add_argument(
            "--directions", action="store_true", help="Enable solar arc directions"
        )
        g.add_argument(
            "--returns", action="store_true", help="Enable solar/lunar returns"
        )
        g.add_argument(
            "--profections", action="store_true", help="Enable annual profections"
        )
        g.add_argument(
            "--prog-aspects",
            action="store_true",
            help="Enable progressed natal aspects detector",
        )
        g.add_argument(
            "--dir-aspects",
            action="store_true",
            help="Enable directed natal aspects detector",
        )
        target._ae_features_added = True


# >>> AUTO-GEN END: cli-new-detector-flags v1.0


DEFAULT_MOVING_BODIES = ["Sun", "Mars", "Jupiter"]


def _normalize_detectors(values: Iterable[str] | None) -> list[str]:
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
    table_rows: list[list[str]] = []
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
    body_lines = [
        " | ".join(value.ljust(widths[idx]) for idx, value in enumerate(row))
        for row in table_rows
    ]
    return "\n".join([header_line, divider, *body_lines])


def _canonical_events_to_dicts(events: Iterable[Any]) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
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
) -> list[str]:
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


def _format_timelord_period(period) -> str:
    extras: list[str] = []
    metadata = period.metadata
    if period.system == "profections":
        house = metadata.get("house")
        sign = metadata.get("sign")
        if house is not None:
            extras.append(f"house {house}")
        if sign:
            extras.append(str(sign))
    elif period.system == "vimshottari":
        parent = metadata.get("parent")
        if parent:
            extras.append(f"parent {parent}")
    elif period.system == "zodiacal_releasing":
        sign = metadata.get("sign")
        if sign:
            extras.append(str(sign))
        if metadata.get("loosing"):
            extras.append("loosing")
    detail = f" ({', '.join(extras)})" if extras else ""
    return f"- {period.system}/{period.level}: {period.ruler}{detail}"


def cmd_timelords_active(args: argparse.Namespace) -> int:
    stack = active_timelords(
        natal_ts=args.natal_utc,
        lat=args.lat,
        lon=args.lon,
        target_ts=args.datetime,
        include_fortune=args.fortune,
        horizon_ts=args.horizon,
    )
    print(f"Active timelords at {stack.moment.isoformat().replace('+00:00', 'Z')}:")
    for period in stack.iter_periods():
        print(_format_timelord_period(period))
    return 0


def cmd_transits(args: argparse.Namespace) -> int:
    engine_module.FEATURE_LUNATIONS = args.lunations
    engine_module.FEATURE_ECLIPSES = args.eclipses
    engine_module.FEATURE_STATIONS = args.stations
    engine_module.FEATURE_PROGRESSIONS = args.progressions
    engine_module.FEATURE_DIRECTIONS = args.directions
    engine_module.FEATURE_RETURNS = args.returns
    engine_module.FEATURE_PROFECTIONS = args.profections

    try:
        resolver = _resolver_for_target_frame(args)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    engine_module.FEATURE_TIMELORDS = getattr(args, "timelords", False)

    timelord_calculator = None
    if engine_module.FEATURE_TIMELORDS:
        if not getattr(args, "natal_utc", None) or args.lat is None or args.lon is None:
            print("timelords overlay requires --natal-utc, --lat, and --lon; disabling")
            engine_module.FEATURE_TIMELORDS = False
        else:
            natal_dt = datetime.fromisoformat(args.natal_utc.replace("Z", "+00:00"))
            horizon = datetime.fromisoformat(
                args.end.replace("Z", "+00:00")
            ) + timedelta(days=1)
            context = build_context(natal_dt, args.lat, args.lon)
            timelord_calculator = TimelordCalculator(context=context, until=horizon)

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
        target_frame=args.target_frame,
        target_resolver=resolver,
        timelord_calculator=timelord_calculator,
        chart_config=getattr(args, "chart_config", None),
        profile_id=args.profile,
        include_declination=True,
        include_mirrors=include_mirrors,
        include_aspects=include_aspects,
        antiscia_axis=args.mirror_axis,
        nodes_variant=args.nodes_variant,
        lilith_variant=args.lilith_variant,
    )

    narrative_bundle = None
    if getattr(args, "narrative", None):
        narrative_bundle = compose_narrative(
            events,
            mode=args.narrative,
            top_n=getattr(args, "narrative_top", 5),
        )

    if args.json:
        payload = {
            "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "parameters": {
                "start_timestamp": args.start,
                "end_timestamp": args.end,
                "moving": args.moving,
                "target": args.target,
                "provider": args.provider,
                "target_longitude": args.target_longitude,
                "target_frame": args.target_frame,
            },
            "events": events_to_dicts(events),
        }
        if narrative_bundle is not None:
            payload["narrative"] = narrative_bundle.to_dict()
        Path(args.json).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Wrote {len(events)} events to {args.json}")

    written = _cli_export(args, events)
    if args.sqlite and written.get("sqlite"):
        print(f"SQLite export complete: {args.sqlite} ({written['sqlite']} rows)")
    if args.parquet and written.get("parquet"):
        print(f"Parquet export complete: {args.parquet} ({written['parquet']} rows)")

    if getattr(args, "export_ics", None):

        if args.ics_summary_template or args.ics_description_template:
            summary_template = args.ics_summary_template or ICS_DEFAULT_SUMMARY_TEMPLATE
            description_template = (
                args.ics_description_template or ICS_DEFAULT_DESCRIPTION_TEMPLATE
            )
            count_ics = write_ics(
                args.export_ics,
                events,
                calendar_name=args.ics_title,
                summary_template=summary_template,
                description_template=description_template,
            )
        else:
            count_ics = write_ics_calendar(
                args.export_ics,
                events,
                title=args.ics_title or "AstroEngine Events",
                narrative_text=narrative_bundle,
            )

        print(f"ICS export complete: {args.export_ics} ({count_ics} events)")

    if not any((args.json, args.sqlite, args.parquet, args.export_ics)):

        print(serialize_events_to_json(events))

    if narrative_bundle is not None:
        print(narrative_bundle.markdown)

    return 0


def cmd_scan(args: argparse.Namespace) -> int:
    detectors = _normalize_detectors(getattr(args, "detectors", None))
    _set_engine_detector_flags(detectors)

    moving = list(dict.fromkeys(args.moving or DEFAULT_MOVING_BODIES))
    frame_selection = list(dict.fromkeys(args.target_frames or [])) or list(
        DEFAULT_TARGET_FRAMES
    )
    targets = _resolve_targets_cli(args.targets, frame_selection)

    entrypoints: list[str] = []
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
            path.write_text(
                json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8"
            )
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


def cmd_query(args: argparse.Namespace) -> int:
    results = top_events_by_score(
        args.sqlite,
        limit=args.limit,
        profile_id=args.profile_id,
        natal_id=args.natal_id,
        moving=args.moving,
        target=args.target,
        year=args.year,
    )
    print(json.dumps(results, indent=2))
    if args.narrative:
        context: Mapping[str, Any] = {}
        for item in args.context or []:
            if "=" in item:
                key, value = item.split("=", 1)
                context[key.strip()] = value.strip()
        timelord_payload = None
        for row in results:
            meta = row.get("meta") or {}
            if isinstance(meta, Mapping) and meta.get("timelords"):
                timelord_payload = meta["timelords"]
                break
        summary = summarize_top_events(
            results,
            top_n=min(len(results), args.limit),
            profile=args.narrative_profile,
            timelords=timelord_payload,
            profile_context=context,
            prefer_template=True,
        )
        print()
        print(summary)
    return 0


def cmd_locational_astrocartography(args: argparse.Namespace) -> int:
    try:
        moment = _parse_iso_datetime(args.moment)
        bodies = (
            [b.strip() for b in args.bodies.split(",") if b.strip()]
            if args.bodies
            else None
        )
        lines = astrocartography_lines(moment, bodies=bodies, lat_step=args.lat_step)
    except Exception as exc:
        print(f"Astrocartography computation failed: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps([line.as_dict() for line in lines], indent=2))
    else:
        for line in lines:
            print(f"{line.body} {line.kind}: {len(line.coordinates)} points")
    return 0


def cmd_locational_local_space(args: argparse.Namespace) -> int:
    try:
        moment = _parse_iso_datetime(args.moment)
        bodies = (
            [b.strip() for b in args.bodies.split(",") if b.strip()]
            if args.bodies
            else None
        )
        vectors = local_space_vectors(moment, args.lat, args.lon, bodies=bodies)
    except Exception as exc:
        print(f"Local-space computation failed: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps([vector.as_dict() for vector in vectors], indent=2))
    else:
        for vector in vectors:
            print(
                f"{vector.body}: azimuth {vector.azimuth_deg:.2f}°, "
                f"altitude {vector.altitude_deg:.2f}°"
            )
    return 0


def _parse_aspect_spec(spec: str | None) -> Mapping[float, str]:
    if not spec:
        return {}
    mapping: dict[float, str] = {}
    defaults = {
        0.0: "conjunction",
        60.0: "sextile",
        90.0: "square",
        120.0: "trine",
        180.0: "opposition",
    }
    for token in spec.split(","):
        token = token.strip()
        if not token:
            continue
        if ":" in token:
            deg_part, label = token.split(":", 1)
        else:
            deg_part, label = token, ""
        try:
            deg_value = float(deg_part)
        except ValueError:
            continue
        mapping[deg_value] = label or defaults.get(deg_value, f"{deg_value:g}°")
    return mapping


def cmd_timeline_outer_cycles(args: argparse.Namespace) -> int:
    try:
        start = _parse_iso_datetime(args.start)
        end = _parse_iso_datetime(args.end)
        bodies = (
            [b.strip() for b in args.bodies.split(",") if b.strip()]
            if args.bodies
            else None
        )
        aspect_mapping = _parse_aspect_spec(args.aspects) or None
        windows = outer_cycle_windows(
            start,
            end,
            bodies=bodies,
            aspects=aspect_mapping,
            step_days=args.step_days,
            orb_allow=args.orb,
        )
    except Exception as exc:
        print(f"Outer-cycle computation failed: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps([window.describe() for window in windows], indent=2))
    else:
        for window in windows:
            aspect = window.metadata.get("aspect") if window.metadata else ""
            print(
                f"{aspect or 'event'}: {window.start.isoformat()} → {window.end.isoformat()}"
            )
    return 0


def cmd_ingresses(args: argparse.Namespace) -> int:
    chart_config = _chart_config_from_args(args)
    adapter = SwissEphemerisAdapter(chart_config=chart_config)
    start_dt = datetime.fromisoformat(args.start.replace("Z", "+00:00")).astimezone(UTC)
    end_dt = datetime.fromisoformat(args.end.replace("Z", "+00:00")).astimezone(UTC)
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
            "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
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
    start_dt = datetime.fromisoformat(args.start.replace("Z", "+00:00")).astimezone(UTC)
    results: list[dict[str, Any]] = []

    if args.vimshottari:
        if args.moon_longitude is None:
            print(
                "timelords: --moon-longitude is required for Vimshottari dashas",
                file=sys.stderr,
            )
            return 1
        levels = [
            level.strip() for level in args.timelord_levels.split(",") if level.strip()
        ]
        periods = compute_vimshottari_dasha(
            args.moon_longitude,
            start_dt,
            cycles=args.dasha_cycles,
            levels=tuple(levels) if levels else ("maha", "antar"),
        )
        results.extend(asdict(event) for event in periods)

    if args.zr:
        if args.fortune_longitude is None:
            print(
                "timelords: --fortune-longitude is required for zodiacal releasing",
                file=sys.stderr,
            )
            return 1
        zr_levels = [
            level.strip() for level in args.zr_levels.split(",") if level.strip()
        ]
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
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "start": args.start,
        "events": results,
    }

    if args.json:
        Path(args.json).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"Wrote {len(results)} periods to {args.json}")
    else:
        print(json.dumps(payload, indent=2))

    return 0


def _add_timelord_compute_args(
    parser: argparse.ArgumentParser, *, required: bool
) -> None:
    parser.add_argument("--start", required=required, help="Start timestamp (ISO-8601)")
    parser.add_argument(
        "--vimshottari", action="store_true", help="Emit Vimśottarī dasha periods"
    )
    parser.add_argument(
        "--moon-longitude",
        type=float,
        help="Moon longitude in degrees for Vimśottarī dashas",
    )
    parser.add_argument(
        "--dasha-cycles",
        type=int,
        default=1,
        help="Number of Vimśottarī cycles to compute",
    )
    parser.add_argument(
        "--timelord-levels",
        default="maha,antar",
        help="Comma-separated Vimśottarī levels to include",
    )
    parser.add_argument(
        "--zr", action="store_true", help="Emit zodiacal releasing periods"
    )
    parser.add_argument(
        "--fortune-longitude", type=float, help="Lot longitude in degrees for releasing"
    )
    parser.add_argument(
        "--zr-periods",
        type=int,
        default=12,
        help="Number of releasing periods to compute",
    )
    parser.add_argument(
        "--zr-levels",
        default="l1,l2",
        help="Comma-separated releasing levels to include",
    )
    parser.add_argument(
        "--lot", default="fortune", help="Lot to use for zodiacal releasing"
    )
    parser.add_argument("--json", help="Write results to this JSON file")


def _dispatch_timelords(args: argparse.Namespace) -> int:
    command = getattr(args, "timelords_command", None)
    if command not in (None, "periods"):
        print(f"timelords: unknown sub-command '{command}'", file=sys.stderr)
        return 1

    if args.start is None:
        print("timelords: --start is required", file=sys.stderr)
        return 1

    return cmd_timelords(args)


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
        help=(
            "Sidereal ayanamsha (required when --zodiac sidereal; default is "
            f"'{DEFAULT_SIDEREAL_AYANAMSHA}')"
        ),
    )
    parser.add_argument(
        "--house-system",
        choices=sorted(VALID_HOUSE_SYSTEMS),
        default="placidus",
        help="Preferred house system for derived charts",
    )
    parser.add_argument(
        "--start-utc", help="Start timestamp (ISO-8601) for experimental detectors"
    )  # ENSURE-LINE
    parser.add_argument(
        "--end-utc", help="End timestamp (ISO-8601) for experimental detectors"
    )  # ENSURE-LINE
    parser.add_argument(
        "--natal-utc", help="Natal timestamp (ISO-8601) for return calculations"
    )  # ENSURE-LINE
    parser.add_argument(
        "--natal-id", help="Natal identifier for provenance and vault operations"
    )  # ENSURE-LINE
    parser.add_argument(
        "--return-kind", default="solar", help="Return kind: solar or lunar"
    )  # ENSURE-LINE

    parser.add_argument(
        "--natal-lat",
        type=float,
        help="Latitude for natal chart when computing mundane aspects",
    )
    parser.add_argument(
        "--natal-lon",
        type=float,
        help="Longitude for natal chart when computing mundane aspects",
    )
    parser.add_argument(
        "--export-sqlite", help="Write precomputed events to this SQLite file"
    )
    parser.add_argument(
        "--export-parquet", help="Write precomputed events to this Parquet file"
    )
    parser.add_argument(
        "--export-ics", help="Write precomputed events to this ICS calendar file"
    )
    parser.add_argument(
        "--ics-title",
        default="AstroEngine Events",
        help="Title to use for ICS export events",
    )
    parser.add_argument(
        "--ics-summary-template", help="Custom summary template for ICS events"
    )
    parser.add_argument(
        "--ics-description-template",
        help="Custom description template for ICS events",
    )

    parser.add_argument(
        "--profile", help="Profile identifier to annotate export metadata"
    )
    parser.add_argument(
        "--lat", type=float, help="Latitude for location-sensitive detectors"
    )
    parser.add_argument(
        "--lon", type=float, help="Longitude for location-sensitive detectors"
    )

    parser.add_argument(
        "--ingresses",
        action="store_true",
        help="Emit sign ingress events between --start-utc and --end-utc",
    )
    parser.add_argument(
        "--ingress-bodies", help="Comma-separated list of bodies for ingress detection"
    )
    parser.add_argument(
        "--ingress-step-hours",
        type=float,
        default=6.0,
        help="Sampling cadence in hours for ingress detection",
    )
    parser.add_argument(
        "--aries-ingress",
        type=int,
        help="Generate Aries ingress chart for the given year",
    )
    parser.add_argument(
        "--aries-quartet",
        action="store_true",
        help="Include solstice/equinox quartet when computing Aries ingress charts",
    )
    parser.add_argument(
        "--mundane-json", help="Write ingress/chart payloads to this JSON path"
    )

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

    parser.add_argument(
        "--aspects", help="Comma-separated aspect angles for natal aspect detectors"
    )
    parser.add_argument(
        "--orb", type=float, help="Orb allowance in degrees for natal aspect detectors"
    )
    # --zodiac, --ayanamsha, and --house-system are declared above; detectors
    # reuse the values from the shared namespace to avoid duplicate options.

    parser.add_argument(
        "--lunations", action="store_true", help="Run lunation detector"
    )
    parser.add_argument("--eclipses", action="store_true", help="Run eclipse detector")
    parser.add_argument(
        "--stations", action="store_true", help="Run planetary station detector"
    )
    parser.add_argument(
        "--progressions", action="store_true", help="Run secondary progression detector"
    )
    parser.add_argument(
        "--directions", action="store_true", help="Run solar arc direction detector"
    )
    parser.add_argument(
        "--returns", action="store_true", help="Run solar/lunar return detector"
    )
    parser.add_argument(
        "--profections",
        action="store_true",
        help="Run annual profection timelord detector",
    )
    parser.add_argument(
        "--timelords",
        action="store_true",
        help="Annotate transit outputs with timelord overlays",
    )
    parser.add_argument(
        "--prog-aspects",
        action="store_true",
        help="Run progressed natal aspect detector",
    )
    parser.add_argument(
        "--dir-aspects", action="store_true", help="Run directed natal aspect detector"
    )
    sub = parser.add_subparsers(dest="command")
    parser._ae_subparsers = sub

    env_parser = sub.add_parser("env", help="List registered providers")
    env_parser.set_defaults(func=cmd_env)

    plugins = sub.add_parser("plugins", help="Inspect plugin runtime and registry")
    plugins.add_argument(
        "--entrypoints", action="store_true", help="List loaded plugin entrypoints"
    )
    plugins.add_argument(
        "--detectors", action="store_true", help="Show detector registrations"
    )
    plugins.add_argument(
        "--score-extensions",
        action="store_true",
        help="Show registered score extension hooks",
    )
    plugins.add_argument(
        "--ui-panels", action="store_true", help="Show UI panel contributions"
    )
    plugins.add_argument(
        "--json", action="store_true", help="Emit JSON payload instead of text"
    )
    plugins.set_defaults(func=cmd_plugins)

    scan = sub.add_parser("scan", help="Run a canonical transit scan with presets")
    scan.add_argument(
        "--start-utc", required=True, help="Window start timestamp (ISO-8601)"
    )
    scan.add_argument(
        "--end-utc", required=True, help="Window end timestamp (ISO-8601)"
    )
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
    scan.add_argument(
        "--export-parquet", help="Write canonical events to a Parquet dataset"
    )
    scan.add_argument(
        "--export-ics", help="Write canonical events to an ICS calendar file"
    )
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
    scan.add_argument(
        "--ayanamsha", help="Sidereal ayanāṁśa to apply when sidereal is enabled"
    )
    scan.set_defaults(func=cmd_scan)

    transits = sub.add_parser("transits", help="Scan for transit contacts")
    feature_targets = getattr(parser, "_ae_feature_parsers", [])
    feature_targets.append(transits)
    parser._ae_feature_parsers = feature_targets
    transits.add_argument("--start", required=True)
    transits.add_argument("--end", required=True)
    transits.add_argument("--moving", default="sun")
    transits.add_argument("--target", default="moon")
    transits.add_argument(
        "--target-frame",
        choices=["natal", "progressed", "directed", "composite"],
        default="natal",
    )
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
    transits.add_argument(
        "--nodes-variant",
        choices=("mean", "true"),
        default="mean",
        help="Lunar node variant to use (default: mean)",
    )
    transits.add_argument(
        "--lilith-variant",
        choices=("mean", "true"),
        default="mean",
        help="Black Moon Lilith variant to use (default: mean)",
    )

    transits.add_argument(
        "--narrative",
        nargs="?",
        choices=["template", "llm"],
        const="template",
        help=(
            "Generate a narrative summary (default template; pass 'llm' to use a "
            "configured model)"
        ),
    )
    transits.add_argument(
        "--narrative-top",
        type=int,
        default=5,
        help="Number of top-scoring events to include in the narrative summary",
    )

    transits.add_argument("--partner-utc")
    transits.add_argument("--partner-lat", type=float)
    transits.add_argument("--partner-lon", type=float)
    transits.add_argument("--json")

    transits.add_argument(
        "--timelords", action="store_true", help="Annotate events with active timelords"
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

    timelords = sub.add_parser("timelords", help="Timelord utilities")
    timelords.set_defaults(func=_dispatch_timelords)
    _add_timelord_compute_args(timelords, required=False)
    tl_sub = timelords.add_subparsers(dest="timelords_command")
    tl_sub.required = True
    active = tl_sub.add_parser("active", help="Show active timelords")
    active.add_argument("--natal-utc", required=True)
    active.add_argument("--lat", type=float, required=True)
    active.add_argument("--lon", type=float, required=True)
    active.add_argument(
        "--datetime", required=True, help="Target timestamp in ISO-8601"
    )
    active.add_argument(
        "--fortune", action="store_true", help="Include Lot of Fortune releasing"
    )
    active.add_argument(
        "--horizon", help="Optional end timestamp for timeline precomputation"
    )
    active.set_defaults(func=cmd_timelords_active)

    generate = tl_sub.add_parser("generate", help="Compute timelord periods")
    generate.add_argument("--start", required=True)
    generate.add_argument("--vimshottari", action="store_true")
    generate.add_argument("--moon-longitude", type=float)
    generate.add_argument("--dasha-cycles", type=int, default=1)
    generate.add_argument(
        "--timelord-levels",
        default="maha,antar",
        help="Comma-separated Vimshottari levels to compute",
    )
    generate.add_argument("--zr", action="store_true")
    generate.add_argument("--fortune-longitude", type=float)
    generate.add_argument("--zr-periods", type=int, default=12)
    generate.add_argument(
        "--zr-levels",
        default="l1,l2",
        help="Comma-separated releasing levels",
    )
    generate.add_argument("--lot", default="fortune")
    generate.add_argument("--json")
    generate.set_defaults(func=cmd_timelords)

    periods = tl_sub.add_parser("periods", help="Compute timelord periods")
    _add_timelord_compute_args(periods, required=True)
    periods.set_defaults(func=_dispatch_timelords)

    validate = sub.add_parser(
        "validate", help="Validate a JSON payload against a schema"
    )
    validate.add_argument("schema", choices=list(available_schema_keys("jsonschema")))
    validate.add_argument("path")
    validate.set_defaults(func=cmd_validate)

    query = sub.add_parser("query", help="Query exported SQLite transit events")
    query.add_argument("--sqlite", required=True, help="Path to the SQLite database")
    query.add_argument(
        "--limit", type=int, default=10, help="Maximum number of rows to return"
    )
    query.add_argument("--profile-id", help="Filter by profile identifier")
    query.add_argument("--natal-id", help="Filter by natal identifier")
    query.add_argument("--moving", help="Filter by moving body")
    query.add_argument("--target", help="Filter by target point")
    query.add_argument("--year", type=int, help="Restrict to calendar year")
    query.add_argument(
        "--narrative",
        action="store_true",
        help="Render narrative summary for the result set",
    )
    query.add_argument(
        "--narrative-profile",
        default="transits",
        help="Narrative profile identifier when --narrative is supplied",
    )
    query.add_argument(
        "--context",
        action="append",
        help="Key=value entries supplying narrative context (repeatable)",
    )
    query.set_defaults(func=cmd_query)

    ops = sub.add_parser("ops", help="Operational helpers")
    ops_sub = ops.add_subparsers(dest="ops_command")
    ops_sub.required = True
    migrate = ops_sub.add_parser(
        "migrate", help="Apply Alembic migrations to SQLite stores"
    )
    migrate.add_argument("--sqlite", required=True, help="SQLite file to migrate")
    migrate.add_argument("--revision", help="Target Alembic revision (default: head)")
    migrate.set_defaults(func=cmd_ops_migrate)

    locational = sub.add_parser("locational", help="Locational visualization datasets")
    loc_sub = locational.add_subparsers(dest="locational_command")
    loc_sub.required = True
    acg = loc_sub.add_parser(
        "astrocartography", help="Compute astrocartography linework"
    )
    acg.add_argument("--moment", required=True, help="UTC timestamp (ISO-8601)")
    acg.add_argument(
        "--bodies", default="", help="Comma-separated body names (optional)"
    )
    acg.add_argument(
        "--lat-step", type=float, default=1.5, help="Latitude sampling step in degrees"
    )
    acg.add_argument("--json", action="store_true", help="Emit JSON output")
    acg.set_defaults(func=cmd_locational_astrocartography)
    local_space = loc_sub.add_parser(
        "local-space", help="Compute local space azimuth vectors"
    )
    local_space.add_argument("--moment", required=True, help="UTC timestamp (ISO-8601)")
    local_space.add_argument(
        "--lat", type=float, required=True, help="Observer latitude in degrees"
    )
    local_space.add_argument(
        "--lon", type=float, required=True, help="Observer longitude in degrees"
    )
    local_space.add_argument(
        "--bodies", default="", help="Comma-separated body names (optional)"
    )
    local_space.add_argument("--json", action="store_true", help="Emit JSON output")
    local_space.set_defaults(func=cmd_locational_local_space)

    timeline = sub.add_parser("timeline", help="Timeline synthesis commands")
    timeline_sub = timeline.add_subparsers(dest="timeline_command")
    timeline_sub.required = True
    outer_cycles = timeline_sub.add_parser(
        "outer-cycles", help="Generate outer planet cycle windows for visualization"
    )
    outer_cycles.add_argument(
        "--start", required=True, help="Start timestamp (ISO-8601)"
    )
    outer_cycles.add_argument("--end", required=True, help="End timestamp (ISO-8601)")
    outer_cycles.add_argument(
        "--bodies", default="", help="Optional comma-separated body list"
    )
    outer_cycles.add_argument(
        "--aspects",
        default="",
        help="Aspect specification (deg[:label], comma separated; default majors)",
    )
    outer_cycles.add_argument(
        "--step-days", type=float, default=1.0, help="Sampling cadence in days"
    )
    outer_cycles.add_argument(
        "--orb", type=float, default=1.0, help="Orb allowance for windows"
    )
    outer_cycles.add_argument("--json", action="store_true", help="Emit JSON output")
    outer_cycles.set_defaults(func=cmd_timeline_outer_cycles)

    ingresses = sub.add_parser("ingresses", help="Detect sign ingress events")
    ingresses.add_argument("--start", required=True)
    ingresses.add_argument("--end", required=True)
    ingresses.add_argument("--bodies", default="Sun")
    ingresses.add_argument("--step-hours", type=float, default=6.0)
    ingresses.add_argument("--json")
    add_canonical_export_args(ingresses)
    ingresses.set_defaults(func=cmd_ingresses)

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
