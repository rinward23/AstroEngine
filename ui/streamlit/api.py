from __future__ import annotations

import os, requests
from typing import Any, Dict

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

class APIClient:
    def __init__(self, base_url: str | None = None) -> None:
        self.base = (base_url or API_BASE_URL).rstrip("/")


    # existing: aspects_search(...)
    def aspects_search(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base}/aspects/search"
        r = requests.post(url, json=payload, timeout=60)
        r.raise_for_status()
        return r.json()

    # ---- OrbPolicy CRUD ---------------------------------------------------
    def list_policies(self, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        r = requests.get(f"{self.base}/policies", params={"limit": limit, "offset": offset}, timeout=30)
        r.raise_for_status(); return r.json()

    def get_policy(self, policy_id: int) -> Dict[str, Any]:
        r = requests.get(f"{self.base}/policies/{policy_id}", timeout=30)
        r.raise_for_status(); return r.json()

    def create_policy(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        r = requests.post(f"{self.base}/policies", json=payload, timeout=30)
        r.raise_for_status(); return r.json()

    def update_policy(self, policy_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        r = requests.put(f"{self.base}/policies/{policy_id}", json=payload, timeout=30)
        r.raise_for_status(); return r.json()



        return self._post_json("/aspects/search", payload, timeout=60)

    # ---- Synastry & Composites -------------------------------------------
    def synastry_compute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._post_json("/synastry/compute", payload, timeout=60)

    def composite_midpoint(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._post_json("/composites/midpoint", payload, timeout=30)

    def composite_davison(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._post_json("/composites/davison", payload, timeout=30)

    # ------------------------------------------------------------------
    def _post_json(self, path: str, payload: Dict[str, Any], *, timeout: int) -> Dict[str, Any]:
        """POST ``payload`` to ``path`` and return the parsed JSON response."""

        if not path.startswith("/"):
            path = f"/{path}"

        url = f"{self.base}{path}"

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

    def electional_search(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke the electional search endpoint."""
        r = requests.post(f"{self.base}/electional/search", json=payload, timeout=90)
        r.raise_for_status()
        return r.json()

