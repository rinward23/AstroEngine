"""HTTP endpoints exposing scan detectors."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, status

from ...detectors.directed_aspects import solar_arc_natal_aspects
from ...detectors.progressed_aspects import progressed_natal_aspects
from ...detectors.returns import solar_lunar_returns
from ...ephemeris import SwissEphemerisAdapter
from ..schemas import ExportSpec, Hit, ScanRequest, ScanResponse
from ...exporters.ics_exporter import write_ics

router = APIRouter()


def _parse_iso(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(UTC)


def _to_mapping(record: Any) -> dict[str, Any]:
    if isinstance(record, dict):
        return dict(record)
    if is_dataclass(record):
        return asdict(record)
    mapping: dict[str, Any] = {}
    for key in (
        "when_iso",
        "ts",
        "timestamp",
        "moving",
        "target",
        "body",
        "planet",
        "reference",
        "chart_point",
        "aspect",
        "aspect_deg",
        "angle_deg",
        "orb",
        "orb_deg",
        "orb_abs",
        "offset_deg",
        "applying",
        "applying_or_separating",
        "retrograde",
        "moving_retrograde",
        "is_retrograde",
    ):
        if hasattr(record, key):
            mapping[key] = getattr(record, key)
    return mapping


def _coerce_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"applying", "yes", "true", "t"}:
            return True
        if lowered in {"separating", "no", "false", "f"}:
            return False
    if isinstance(value, (int, float)):
        return bool(value)
    return None


def _extract_aspect(mapping: dict[str, Any]) -> int:
    for key in ("aspect", "aspect_deg", "angle_deg"):
        value = mapping.get(key)
        if value is None:
            continue
        try:
            return int(round(float(value)))
        except (TypeError, ValueError):
            continue
    kind = mapping.get("kind")
    if isinstance(kind, str):
        table = {
            "conjunction": 0,
            "sextile": 60,
            "square": 90,
            "trine": 120,
            "opposition": 180,
        }
        lowered = kind.strip().lower()
        if lowered in table:
            return table[lowered]
    return 0


def _extract_orb(mapping: dict[str, Any]) -> float:
    for key in ("orb", "orb_deg", "orb_abs", "offset_deg"):
        value = mapping.get(key)
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return 0.0


def _record_to_hit(record: Any) -> Hit:
    data = _to_mapping(record)
    when = data.get("when_iso") or data.get("ts") or data.get("timestamp")
    if not when:
        raise ValueError("record missing timestamp information")
    moving = data.get("moving") or data.get("body") or data.get("planet")
    target = data.get("target") or data.get("reference") or data.get("chart_point")
    if not moving or not target:
        raise ValueError("record missing moving/target identifiers")

    aspect = _extract_aspect(data)
    orb = _extract_orb(data)
    applying = _coerce_bool(
        data.get("applying") or data.get("applying_or_separating")
    )
    retrograde = data.get("retrograde")
    if retrograde is None:
        retrograde = data.get("moving_retrograde") or data.get("is_retrograde")
    retrograde_bool = _coerce_bool(retrograde)

    return Hit(
        when_iso=str(when),
        moving=str(moving),
        target=str(target),
        aspect=int(aspect),
        orb=float(orb),
        applying=applying,
        retrograde=retrograde_bool,
    )


def _summarise(hits: Iterable[Hit]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    total = 0
    for hit in hits:
        counter[str(hit.aspect)] += 1
        total += 1
    counter["total"] = total
    return dict(counter)


def _export_hits(spec: ExportSpec | None, hits: Sequence[Hit]) -> ExportSpec | None:
    if spec is None or spec.format == "json":
        return spec

    if not spec.path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="export.path is required for non-JSON exports",
        )

    destination = Path(spec.path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    if spec.format == "ics":
        write_ics(destination, hits)
        return spec

    if spec.format == "parquet":
        _write_hits_parquet(destination, hits)
        return spec

    if spec.format == "sqlite":
        _write_hits_sqlite(destination, hits)
        return spec

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Unsupported export format '{spec.format}'",
    )


def _write_hits_parquet(path: Path, hits: Sequence[Hit]) -> None:
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except Exception as exc:  # pragma: no cover - optional dependency
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Parquet export requires pyarrow",
        ) from exc

    rows = [hit.model_dump() for hit in hits]
    table = pa.Table.from_pylist(rows)
    pq.write_table(table, str(path))


def _write_hits_sqlite(path: Path, hits: Sequence[Hit]) -> None:
    try:
        import sqlite3
    except Exception as exc:  # pragma: no cover - optional dependency
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="SQLite export requires sqlite3",
        ) from exc

    con = sqlite3.connect(str(path))
    try:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS scan_hits (
                when_iso TEXT,
                moving TEXT,
                target TEXT,
                aspect INTEGER,
                orb REAL,
                applying INTEGER,
                retrograde INTEGER
            )
            """
        )
        con.executemany(
            """
            INSERT INTO scan_hits (when_iso, moving, target, aspect, orb, applying, retrograde)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    hit.when_iso,
                    hit.moving,
                    hit.target,
                    hit.aspect,
                    hit.orb,
                    None if hit.applying is None else int(hit.applying),
                    None if hit.retrograde is None else int(hit.retrograde),
                )
                for hit in hits
            ],
        )
        con.commit()
    finally:
        con.close()


def _validate_method(request: ScanRequest, expected: str) -> None:
    if request.method != expected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"method must be '{expected}' for this endpoint",
        )


def _require_natal(request: ScanRequest) -> str:
    natal = request.natal_inline
    if natal is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="natal_inline is required for this scan",
        )
    return natal.ts


def _build_response(
    method: str,
    request: ScanRequest,
    records: Sequence[Any],
) -> ScanResponse:
    hits = [_record_to_hit(record) for record in records]
    summary = _summarise(hits)
    export_spec = _export_hits(request.export, hits)
    return ScanResponse(
        method=method,
        count=len(hits),
        summary=summary,
        export=export_spec,
        hits=hits,
    )


@router.post("/progressions", response_model=ScanResponse)
def scan_progressions(request: ScanRequest) -> ScanResponse:
    """Scan progressed aspects derived from a natal chart."""

    _validate_method(request, "progressions")
    natal_ts = _require_natal(request)
    try:
        records = progressed_natal_aspects(
            natal_ts=natal_ts,
            start_ts=request.from_,
            end_ts=request.to,
            aspects=request.aspects,
            orb_deg=request.orb_deg,
        )
    except NotImplementedError as exc:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=str(exc),
        ) from exc
    return _build_response("progressions", request, records)


@router.post("/directions", response_model=ScanResponse)
def scan_directions(request: ScanRequest) -> ScanResponse:
    """Scan solar arc directed aspects."""

    _validate_method(request, "directions")
    natal_ts = _require_natal(request)
    try:
        records = solar_arc_natal_aspects(
            natal_ts=natal_ts,
            start_ts=request.from_,
            end_ts=request.to,
            aspects=request.aspects,
            orb_deg=request.orb_deg,
        )
    except NotImplementedError as exc:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=str(exc),
        ) from exc
    return _build_response("directions", request, records)


@router.post("/transits", response_model=ScanResponse)
def scan_transits(request: ScanRequest) -> ScanResponse:
    """Transit scanning is not yet wired into the HTTP API."""

    _validate_method(request, "transits")
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Transit scanning is not yet available via the HTTP API",
    )


@router.post("/returns", response_model=ScanResponse)
def scan_returns(request: ScanRequest) -> ScanResponse:
    """Solar or lunar returns derived from a natal timestamp."""

    _validate_method(request, "returns")
    natal_ts = _require_natal(request)
    adapter = SwissEphemerisAdapter.get_default_adapter()
    natal_jd = adapter.julian_day(_parse_iso(natal_ts))
    start_jd = adapter.julian_day(_parse_iso(request.from_))
    end_jd = adapter.julian_day(_parse_iso(request.to))
    kind = (request.dataset or "solar").split(":", 1)[0]

    try:
        events = solar_lunar_returns(
            natal_jd,
            start_jd,
            end_jd,
            kind=kind,
        )
    except NotImplementedError as exc:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=str(exc),
        ) from exc

    hits = [
        Hit(
            when_iso=event.ts,
            moving=event.body,
            target=f"natal_{event.body}",
            aspect=0,
            orb=0.0,
            applying=None,
            retrograde=None,
        )
        for event in events
    ]
    summary = _summarise(hits)
    export_spec = _export_hits(request.export, hits)
    return ScanResponse(
        method="returns",
        count=len(hits),
        summary=summary,
        export=export_spec,
        hits=hits,
    )
