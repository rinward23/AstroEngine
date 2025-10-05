"""Chart-centric API endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Response
from sqlalchemy import select

from astroengine.chart.natal import ChartLocation, compute_natal_chart
from astroengine.config import load_settings
from astroengine.report import render_chart_pdf
from astroengine.report.builders import build_chart_report_context
from app.db.models import Chart
from app.db.session import session_scope

router = APIRouter(prefix="/v1/charts", tags=["charts"])


@router.get("/{chart_id}/pdf")
def chart_pdf(chart_id: int) -> Response:
    settings = load_settings()
    if not settings.reports.pdf_enabled:
        raise HTTPException(status_code=403, detail="PDF reports are disabled")

    with session_scope() as db:
        chart = db.execute(select(Chart).where(Chart.id == chart_id)).scalar_one_or_none()
        if chart is None:
            raise HTTPException(status_code=404, detail="Chart not found")
        if chart.dt_utc is None or chart.lat is None or chart.lon is None:
            raise HTTPException(status_code=400, detail="Chart is missing birth data")
        moment = chart.dt_utc
        # SQLite often round-trips timestamps without timezone info. Treat stored
        # UTC datetimes as UTC explicitly so Swiss ephemeris adapters accept them.
        if moment.tzinfo is None or moment.tzinfo.utcoffset(moment) is None:
            moment = moment.replace(tzinfo=timezone.utc)

        location = ChartLocation(latitude=float(chart.lat), longitude=float(chart.lon))
        natal = compute_natal_chart(moment, location)

    context = build_chart_report_context(
        chart_id=chart_id,
        natal=natal,
        chart_kind=str(chart.kind) if chart.kind else None,
        profile_key=chart.profile_key,
        chart_timestamp=moment,
        location_name=chart.location_name,
        disclaimers=settings.reports.disclaimers,
        generated_at=datetime.now(timezone.utc),
    )
    pdf_bytes = render_chart_pdf(context)
    headers = {
        "Content-Disposition": f'attachment; filename="chart_{chart_id}.pdf"'
    }
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)


__all__ = ["router"]
