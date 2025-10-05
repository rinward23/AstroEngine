"""Chart-centric API endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, Response, status

from astroengine.chart.natal import ChartLocation, compute_natal_chart
from astroengine.config import load_settings
from astroengine.report import render_chart_pdf
from astroengine.report.builders import build_chart_report_context
from app.db.session import session_scope
from app.repo.charts import ChartRepo
from app.schemas.charts import ChartSummary, ChartTagsUpdate

router = APIRouter(prefix="/v1/charts", tags=["charts"])


@router.get("", response_model=list[ChartSummary])
def list_charts(
    q: str | None = Query(
        default=None, description="Case-insensitive search across chart keys."
    ),
    tag: list[str] = Query(
        default_factory=list,
        description="Filter charts containing all provided tags.",
    ),
    created_from: datetime | None = Query(default=None),
    created_to: datetime | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[ChartSummary]:
    with session_scope() as db:
        records = ChartRepo().search(
            db,
            query=q,
            tags=tag or None,
            created_from=created_from,
            created_to=created_to,
            limit=limit,
            offset=offset,
        )
        return [ChartSummary.model_validate(record) for record in records]


@router.get("/deleted", response_model=list[ChartSummary])
def list_deleted_charts(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[ChartSummary]:
    with session_scope() as db:
        records = ChartRepo().list_deleted(db, limit=limit, offset=offset)
        return [ChartSummary.model_validate(record) for record in records]


@router.patch("/{chart_id}/tags", response_model=ChartSummary)
def update_chart_tags(chart_id: int, payload: ChartTagsUpdate) -> ChartSummary:
    with session_scope() as db:
        repo = ChartRepo()
        try:
            chart = repo.update_tags(db, chart_id, payload.tags)
        except ValueError as exc:  # pragma: no cover - defensive guard
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        db.refresh(chart)
        return ChartSummary.model_validate(chart)


@router.delete("/{chart_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chart(chart_id: int) -> Response:
    with session_scope() as db:
        chart = ChartRepo().soft_delete(db, chart_id)
        if chart is None:
            raise HTTPException(status_code=404, detail="Chart not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{chart_id}/restore", response_model=ChartSummary)
def restore_chart(chart_id: int) -> ChartSummary:
    with session_scope() as db:
        chart = ChartRepo().restore(db, chart_id)
        if chart is None:
            raise HTTPException(
                status_code=404, detail="Chart not found or not deleted"
            )
        db.refresh(chart)
        return ChartSummary.model_validate(chart)


@router.get("/{chart_id}/pdf")
def chart_pdf(chart_id: int) -> Response:
    settings = load_settings()
    if not settings.reports.pdf_enabled:
        raise HTTPException(status_code=403, detail="PDF reports are disabled")

    with session_scope() as db:
        repo = ChartRepo()
        chart = repo.get(db, chart_id, include_deleted=True)
        if chart is None or chart.deleted_at is not None:
            raise HTTPException(status_code=404, detail="Chart not found")
        if chart.dt_utc is None or chart.lat is None or chart.lon is None:
            raise HTTPException(status_code=400, detail="Chart is missing birth data")
        moment = chart.dt_utc
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

