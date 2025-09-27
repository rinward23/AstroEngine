from __future__ import annotations
import os
from typing import Any, Dict

import requests

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


def _extract_error_message(response: requests.Response | None) -> str | None:
    """Best-effort extraction of a useful error message from an HTTP response."""

    if response is None:
        return None

    try:
        payload = response.json()
    except ValueError:
        text = response.text.strip()
        return text or None

    if isinstance(payload, dict):
        detail = payload.get("detail")
        if isinstance(detail, str) and detail.strip():
            return detail.strip()
        # FastAPI may return a list of errors under ``detail``
        if isinstance(detail, list) and detail:
            first = detail[0]
            if isinstance(first, dict):
                msg = first.get("msg")
                if isinstance(msg, str) and msg.strip():
                    return msg.strip()
    return None


class APIClient:
    def __init__(self, base_url: str | None = None) -> None:
        self.base = (base_url or API_BASE_URL).rstrip("/")

    # ---- Internal helpers --------------------------------------------------
    def _post_json(self, path: str, payload: Dict[str, Any], timeout: int = 60) -> Any:
        """Send a POST request and return the decoded JSON body."""

        url = f"{self.base}{path if path.startswith('/') else '/' + path}"
        try:
            response = requests.post(url, json=payload, timeout=timeout)
            response.raise_for_status()
        except requests.HTTPError as exc:  # pragma: no cover - streamlit UI only
            message = _extract_error_message(exc.response) or str(exc)
            raise RuntimeError(message) from exc
        except requests.RequestException as exc:  # pragma: no cover - streamlit UI only
            raise RuntimeError(str(exc)) from exc

        try:
            return response.json()
        except ValueError as exc:  # pragma: no cover - streamlit UI only
            raise RuntimeError("API returned a non-JSON response") from exc

    def aspects_search(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Call the aspect search endpoint and return the parsed JSON body."""

        data = self._post_json("/aspects/search", payload)
        if not isinstance(data, dict):  # pragma: no cover - defensive
            raise RuntimeError("Unexpected response payload from /aspects/search")
        return data

    # ---- Events ------------------------------------------------------------
    def voc_moon(self, payload: Dict[str, Any]) -> list[Dict[str, Any]]:
        data = self._post_json("/events/voc-moon", payload)
        if not isinstance(data, list):  # pragma: no cover - defensive
            raise RuntimeError("Unexpected response payload from /events/voc-moon")
        return data

    def combust_cazimi(self, payload: Dict[str, Any]) -> list[Dict[str, Any]]:
        data = self._post_json("/events/combust-cazimi", payload)
        if not isinstance(data, list):  # pragma: no cover - defensive
            raise RuntimeError("Unexpected response payload from /events/combust-cazimi")
        return data

    def returns(self, payload: Dict[str, Any]) -> list[Dict[str, Any]]:
        data = self._post_json("/events/returns", payload)
        if not isinstance(data, list):  # pragma: no cover - defensive
            raise RuntimeError("Unexpected response payload from /events/returns")
        return data
