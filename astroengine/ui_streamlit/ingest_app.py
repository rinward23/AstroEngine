"""Streamlit helpers for ingest flows."""
from __future__ import annotations

from astroengine.api.ingest import IngestAPI


def parse_voice(api: IngestAPI, transcript: str):
    return api.ingest_voice(transcript)


def parse_vision(api: IngestAPI, text: str):
    return api.ingest_vision(text)
