"""CRUD endpoints for chart notes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response, status

from app.db.session import session_scope
from app.repo.charts import ChartRepo
from app.repo.notes import NoteRepo
from app.schemas.notes import NoteCreate, NoteOut

router = APIRouter(prefix="/v1", tags=["notes"])


@router.get("/notes", response_model=list[NoteOut])
def list_notes(chart_id: int | None = None) -> list[NoteOut]:
    """Return all notes, optionally filtered by ``chart_id``."""

    with session_scope() as db:
        repo = NoteRepo()
        if chart_id is not None:
            chart = ChartRepo().get(db, chart_id)
            if chart is None:
                raise HTTPException(status_code=404, detail="Chart not found")
            notes = repo.list_by_chart(db, chart_id)
        else:
            notes = repo.list_all(db)
        return [NoteOut.model_validate(note) for note in notes]


@router.get("/charts/{chart_id}/notes", response_model=list[NoteOut])
def list_chart_notes(chart_id: int) -> list[NoteOut]:
    """Return notes associated with a specific chart."""

    with session_scope() as db:
        chart = ChartRepo().get(db, chart_id)
        if chart is None:
            raise HTTPException(status_code=404, detail="Chart not found")
        notes = NoteRepo().list_by_chart(db, chart_id)
        return [NoteOut.model_validate(note) for note in notes]


@router.post("/notes", response_model=NoteOut, status_code=status.HTTP_201_CREATED)
def create_note(payload: NoteCreate) -> NoteOut:
    """Create a new note for the provided chart."""

    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="Note text cannot be empty")

    with session_scope() as db:
        chart = ChartRepo().get(db, payload.chart_id)
        if chart is None:
            raise HTTPException(status_code=404, detail="Chart not found")
        repo = NoteRepo()
        record = repo.create(
            db,
            chart_id=payload.chart_id,
            text=payload.text.strip(),
            tags=list(dict.fromkeys(payload.tags)),
        )
        db.refresh(record)
        return NoteOut.model_validate(record)


@router.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(note_id: int) -> Response:
    """Delete a note by identifier."""

    with session_scope() as db:
        repo = NoteRepo()
        record = repo.get(db, note_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Note not found")
        repo.delete(db, note_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__ = ["router"]
