"""Minimal FastAPI server exposing detector endpoints."""

from __future__ import annotations

try:  # pragma: no cover - optional dependency
    from fastapi import FastAPI
except Exception:  # pragma: no cover - optional dependency
    FastAPI = None  # type: ignore[assignment]


app = FastAPI(title="AstroEngine API") if FastAPI is not None else None


# >>> AUTO-GEN BEGIN: api-detectors v1.0
if app:
    from fastapi import Query
    from .detectors import find_lunations, find_stations, solar_lunar_returns, secondary_progressions, solar_arc_directions

    @app.get("/detectors/lunations")
    def api_lunations(start_jd: float = Query(...), end_jd: float = Query(...)):
        return [e.__dict__ for e in find_lunations(start_jd, end_jd)]

    @app.get("/detectors/stations")
    def api_stations(start_jd: float = Query(...), end_jd: float = Query(...)):
        return [e.__dict__ for e in find_stations(start_jd, end_jd, None)]

    @app.get("/detectors/returns")
    def api_returns(natal_jd: float = Query(...), start_jd: float = Query(...), end_jd: float = Query(...), which: str = Query("solar")):
        return [e.__dict__ for e in solar_lunar_returns(natal_jd, start_jd, end_jd, which)]

    @app.get("/detectors/progressions")
    def api_progressions(natal_ts: str = Query(...), start_ts: str = Query(...), end_ts: str = Query(...)):
        return [e.__dict__ for e in secondary_progressions(natal_ts, start_ts, end_ts)]

    @app.get("/detectors/directions")
    def api_directions(natal_ts: str = Query(...), start_ts: str = Query(...), end_ts: str = Query(...)):
        return [e.__dict__ for e in solar_arc_directions(natal_ts, start_ts, end_ts)]
# >>> AUTO-GEN END: api-detectors v1.0


__all__ = ["app"]
