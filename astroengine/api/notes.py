"""API surface for diary notes."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from astroengine.engine.notes.crdt import CRDTDocument
from astroengine.engine.notes.store import NotesStore


@dataclass
class NoteRequest:
    note_id: str
    owner_id: str
    patch: dict


@dataclass
class NoteResponse:
    note_id: str
    title: str
    tags: list[str]
    body: str


class NotesAPI:
    def __init__(self, store: NotesStore) -> None:
        self.store = store

    def post_note(self, request: NoteRequest) -> NoteResponse:
        document = CRDTDocument(device_id=request.owner_id)
        document.apply_patch(request.patch)
        record = self.store.upsert_from_crdt(request.note_id, request.owner_id, document)
        return NoteResponse(
            note_id=record.note_id,
            title=record.title,
            tags=list(record.tags),
            body=record.decrypted_body(self.store.cipher),
        )

    def get_notes(self, owner_id: str, query: str = "", tags: Iterable[str] | None = None) -> list[NoteResponse]:
        responses: list[NoteResponse] = []
        for record in self.store.search(owner_id=owner_id, query=query, tags=tags):
            responses.append(
                NoteResponse(
                    note_id=record.note_id,
                    title=record.title,
                    tags=list(record.tags),
                    body=record.decrypted_body(self.store.cipher),
                )
            )
        return responses
