"""Utility helpers mirroring the Streamlit NLP lab."""
from __future__ import annotations

from astroengine.api.nlp import NLPAPI, NLPRequest, NLPResponse


def run_lab(api: NLPAPI, request: NLPRequest) -> NLPResponse:
    return api.run(request)
