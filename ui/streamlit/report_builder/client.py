"""HTTP client for relationship interpretation APIs."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

import requests


@dataclass(slots=True)
class APIError(Exception):
    """Lightweight exception for surfacing API failures."""

    message: str
    status: int | None = None

    def __str__(self) -> str:  # pragma: no cover - trivial
        if self.status is None:
            return self.message
        return f"{self.message} (HTTP {self.status})"


def _normalise_base(url: str) -> str:
    """Ensure the base URL does not end with a trailing slash."""

    return url.rstrip("/") if url else ""


def _extract_detail(response: requests.Response | None) -> str | None:
    """Attempt to pull a human friendly error message from a response."""

    if response is None:
        return None

    try:
        payload = response.json()
    except ValueError:
        text = (response.text or "").strip()
        return text or None

    if isinstance(payload, dict):
        detail = payload.get("detail")
        if isinstance(detail, str) and detail.strip():
            return detail.strip()
        if isinstance(detail, Iterable) and not isinstance(detail, (str, bytes)):
            first = next((item for item in detail if isinstance(item, str) and item.strip()), None)
            if first:
                return first.strip()
        for key in ("message", "error"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


class RelationshipClient:
    """Thin wrapper around the relationship interpretation endpoints."""

    def __init__(self, relationship_base: str, interpretation_base: str | None = None) -> None:
        if not relationship_base:
            raise ValueError("relationship_base must be provided")
        self.relationship_base = _normalise_base(relationship_base)
        self.interpretation_base = _normalise_base(interpretation_base or relationship_base)

    # ------------------------------------------------------------------
    # REST helpers
    def _post(self, base: str, path: str, payload: dict[str, Any], *, timeout: int) -> dict[str, Any] | list[Any]:
        url = f"{base}{path}" if path.startswith("/") else f"{base}/{path}"
        try:
            response = requests.post(url, json=payload, timeout=timeout)
        except requests.RequestException as exc:  # pragma: no cover - network
            raise APIError(str(exc)) from exc

        if response.status_code >= 400:
            message = _extract_detail(response) or response.text or "Unknown API error"
            raise APIError(message, response.status_code)

        try:
            return response.json()
        except ValueError as exc:  # pragma: no cover - defensive
            raise APIError("API returned a non-JSON response") from exc

    def _get(self, base: str, path: str, *, timeout: int) -> dict[str, Any] | list[Any]:
        url = f"{base}{path}" if path.startswith("/") else f"{base}/{path}"
        try:
            response = requests.get(url, timeout=timeout)
        except requests.RequestException as exc:  # pragma: no cover - network
            raise APIError(str(exc)) from exc

        if response.status_code >= 400:
            message = _extract_detail(response) or response.text or "Unknown API error"
            raise APIError(message, response.status_code)

        try:
            return response.json()
        except ValueError as exc:  # pragma: no cover - defensive
            raise APIError("API returned a non-JSON response") from exc

    # ------------------------------------------------------------------
    # Public endpoints
    def synastry(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Invoke the B-003 synastry endpoint and return the response body."""

        data = self._post(self.relationship_base, "/v1/relationship/synastry", payload, timeout=90)
        if not isinstance(data, dict):  # pragma: no cover - defensive
            raise APIError("Unexpected response payload from synastry endpoint")
        return data

    def interpret(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Invoke the B-006 relationship interpretation endpoint."""

        data = self._post(self.interpretation_base, "/v1/interpret/relationship", payload, timeout=90)
        if not isinstance(data, dict):  # pragma: no cover - defensive
            raise APIError("Unexpected response payload from interpret endpoint")
        return data

    def list_rulepacks(self) -> list[dict[str, Any]]:
        """Return available rulepacks for relationship interpretations."""

        data = self._get(self.interpretation_base, "/v1/interpret/rulepacks", timeout=60)
        if isinstance(data, dict):
            items = data.get("items") if isinstance(data, dict) else None
            if isinstance(items, list):
                data = items
        if not isinstance(data, list):  # pragma: no cover - defensive
            raise APIError("Unexpected response payload from rulepack listing")
        return data
