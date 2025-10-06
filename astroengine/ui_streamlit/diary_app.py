"""Streamlit scaffolding for the diary experience."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from astroengine.api.notes import NoteRequest, NotesAPI


@dataclass
class DiaryState:
    owner_id: str
    device_id: str


class DiaryStreamlitApp:
    def __init__(self, api: NotesAPI, state: DiaryState) -> None:
        self.api = api
        self.state = state

    def create_note(self, note_id: str, title: str, body: str, tags: Iterable[str]) -> None:
        request = NoteRequest(note_id=note_id, owner_id=self.state.owner_id, patch={"title": title, "body": body, "tags": list(tags)})
        self.api.post_note(request)

    def search(self, query: str = "", tags: Iterable[str] | None = None) -> list[str]:
        responses = self.api.get_notes(owner_id=self.state.owner_id, query=query, tags=tags)
        return [response.title for response in responses]
