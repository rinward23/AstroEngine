from __future__ import annotations

import os
from typing import Any, Dict, Iterable, Optional, Sequence

import requests
from requests import Response

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


def _extract_error_message(response: Optional[Response]) -> Optional[str]:
    """Attempt to pull a human-friendly error message from a response."""

    if response is None:
        return None

    # Try JSON first – FastAPI typically returns {"detail": ...}
    try:
        data = response.json()
    except ValueError:
        text = response.text.strip()
        return text or None

    if isinstance(data, dict):
        for key in ("detail", "message", "error"):
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
            if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
                first = next((item for item in value if isinstance(item, str) and item.strip()), None)
                if first:
                    return first.strip()
    return None


class APIClient:
    def __init__(self, base_url: str | None = None) -> None:
        self.base = (base_url or API_BASE_URL).rstrip("/")

    # ---- Low-level helpers -------------------------------------------------
    def _post_json(
        self,
        path: str,
        payload: Dict[str, Any],
        *,
        timeout: int,
        params: Dict[str, Any] | None = None,
    ) -> Dict[str, Any] | list[Any]:
        """POST ``payload`` to ``path`` and return the parsed JSON response."""

        if not path.startswith("/"):
            path = f"/{path}"

        url = f"{self.base}{path}"
        try:
            response = requests.post(url, json=payload, params=params, timeout=timeout)
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

    # ---- Natals ------------------------------------------------------------
    def list_natals(self, page: int = 1, page_size: int = 100) -> Dict[str, Any]:
        """Return a page of stored natal charts."""

        response = requests.get(
            f"{self.base}/v1/natals",
            params={"page": page, "page_size": page_size},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):  # pragma: no cover - defensive
            raise RuntimeError("Unexpected response payload from /v1/natals")
        return data

    # ---- Analysis ----------------------------------------------------------
    def analysis_lots(self, natal_id: str) -> Dict[str, Any]:
        """Compute Arabic Parts for ``natal_id`` via the analysis endpoint."""

        response = requests.get(
            f"{self.base}/v1/analysis/lots",
            params={"natal_id": natal_id},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):  # pragma: no cover - defensive
            raise RuntimeError("Unexpected response payload from /v1/analysis/lots")
        return data

    # ---- Aspects -----------------------------------------------------------
    def aspects_search(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Call the aspect search endpoint and return the parsed JSON body."""

        data = self._post_json("/aspects/search", payload, timeout=60)
        if not isinstance(data, dict):  # pragma: no cover - defensive
            raise RuntimeError("Unexpected response payload from /aspects/search")
        return data

    def declination_aspects(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke the declination aspects endpoint and return the JSON payload."""

        data = self._post_json("/declinations/aspects", payload, timeout=30)
        if not isinstance(data, dict):  # pragma: no cover - defensive
            raise RuntimeError(
                "Unexpected response payload from /declinations/aspects"
            )
        return data

    # ---- OrbPolicy CRUD ----------------------------------------------------
    def list_policies(self, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        r = requests.get(
            f"{self.base}/policies",
            params={"limit": limit, "offset": offset},
            timeout=30,
        )
        r.raise_for_status()
        return r.json()

    def get_policy(self, policy_id: int) -> Dict[str, Any]:
        r = requests.get(f"{self.base}/policies/{policy_id}", timeout=30)
        r.raise_for_status()
        return r.json()

    def create_policy(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        r = requests.post(f"{self.base}/policies", json=payload, timeout=30)
        r.raise_for_status()
        return r.json()

    def update_policy(self, policy_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        r = requests.put(f"{self.base}/policies/{policy_id}", json=payload, timeout=30)
        r.raise_for_status()
        return r.json()

    # ---- Natals -----------------------------------------------------------
    def list_natals(self, limit: int = 250) -> list[Dict[str, Any]]:
        r = requests.get(
            f"{self.base}/v1/natals",
            params={"page_size": limit},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        items = data.get("items") if isinstance(data, dict) else None
        if not isinstance(items, list):  # pragma: no cover - defensive
            raise RuntimeError("Unexpected response payload from /v1/natals")
        return items

    # ---- Forecast ---------------------------------------------------------
    def forecast_stack(
        self,
        natal_id: str,
        start_iso: str,
        end_iso: str,
        *,
        techniques: list[str] | None = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"natal_id": natal_id, "from": start_iso, "to": end_iso}
        if techniques:
            params["techniques"] = techniques
        r = requests.get(f"{self.base}/v1/forecast", params=params, timeout=60)
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, dict):  # pragma: no cover - defensive
            raise RuntimeError("Unexpected response payload from /v1/forecast")
        return data

    def forecast_stack_csv(
        self,
        natal_id: str,
        start_iso: str,
        end_iso: str,
        *,
        techniques: list[str] | None = None,
    ) -> str:
        params: Dict[str, Any] = {
            "natal_id": natal_id,
            "from": start_iso,
            "to": end_iso,
            "format": "csv",
        }
        if techniques:
            params["techniques"] = techniques
        r = requests.get(f"{self.base}/v1/forecast", params=params, timeout=60)
        r.raise_for_status()
        return r.text

    # ---- Synastry & Composites --------------------------------------------
    def synastry_compute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        data = self._post_json("/synastry/compute", payload, timeout=60)
        if not isinstance(data, dict):  # pragma: no cover - defensive
            raise RuntimeError("Unexpected response payload from /synastry/compute")
        return data

    def composite_midpoint(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        data = self._post_json("/composites/midpoint", payload, timeout=30)
        if not isinstance(data, dict):  # pragma: no cover - defensive
            raise RuntimeError("Unexpected response payload from /composites/midpoint")
        return data

    def composite_davison(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        data = self._post_json("/composites/davison", payload, timeout=30)
        if not isinstance(data, dict):  # pragma: no cover - defensive
            raise RuntimeError("Unexpected response payload from /composites/davison")
        return data

    # ---- Events ------------------------------------------------------------
    def voc_moon(self, payload: Dict[str, Any]) -> list[Dict[str, Any]]:
        data = self._post_json("/events/voc-moon", payload, timeout=60)
        if not isinstance(data, list):  # pragma: no cover - defensive
            raise RuntimeError("Unexpected response payload from /events/voc-moon")
        return data

    def combust_cazimi(self, payload: Dict[str, Any]) -> list[Dict[str, Any]]:
        data = self._post_json("/events/combust-cazimi", payload, timeout=60)
        if not isinstance(data, list):  # pragma: no cover - defensive
            raise RuntimeError("Unexpected response payload from /events/combust-cazimi")
        return data

    def returns(self, payload: Dict[str, Any]) -> list[Dict[str, Any]]:
        data = self._post_json("/events/returns", payload, timeout=60)
        if not isinstance(data, list):  # pragma: no cover - defensive
            raise RuntimeError("Unexpected response payload from /events/returns")
        return data

    # ---- Data IO -----------------------------------------------------------
    def export_bundle(self, scope: Sequence[str] | None = None) -> bytes:
        """Download a ZIP archive of stored charts and configuration."""

        scope_parts = [str(item).strip() for item in (scope or []) if str(item).strip()]
        scope_value = ",".join(scope_parts) if scope_parts else "charts,settings"
        try:
            response = requests.get(
                f"{self.base}/v1/export",
                params={"scope": scope_value},
                timeout=60,
            )
            response.raise_for_status()
        except requests.HTTPError as exc:  # pragma: no cover - streamlit UI only
            message = _extract_error_message(exc.response) or str(exc)
            raise RuntimeError(message) from exc
        except requests.RequestException as exc:  # pragma: no cover - streamlit UI only
            raise RuntimeError(str(exc)) from exc
        return response.content

    # ---- Timeline ---------------------------------------------------------
    def timeline(
        self,
        start_iso: str,
        end_iso: str,
        *,
        types: Sequence[str] | None = None,
        bodies: Sequence[str] | None = None,
        sign_orb: float | None = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"from": start_iso, "to": end_iso}
        if types:
            params["types"] = ",".join(types)
        if bodies:
            params["bodies"] = ",".join(bodies)
        if sign_orb is not None:
            params["sign_orb"] = float(sign_orb)
        r = requests.get(f"{self.base}/v1/timeline", params=params, timeout=60)
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, dict):  # pragma: no cover - defensive
            raise RuntimeError("Unexpected response payload from /v1/timeline")
        return data

    def electional_search(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke the electional search endpoint."""

        r = requests.post(f"{self.base}/v1/electional/search", json=payload, timeout=90)
        r.raise_for_status()
        return r.json()

    # ---- Analysis ---------------------------------------------------------
    def dignities_analysis(self, natal_id: str) -> Dict[str, Any]:
        """Retrieve Lilly dignity report for a stored natal chart."""

        params = {"natal_id": natal_id}
        try:
            response = requests.get(
                f"{self.base}/v1/analysis/dignities", params=params, timeout=30
            )
            response.raise_for_status()
        except requests.HTTPError as exc:  # pragma: no cover - UI path only
            message = _extract_error_message(exc.response) or str(exc)
            raise RuntimeError(message) from exc
        except requests.RequestException as exc:  # pragma: no cover - UI path only
            raise RuntimeError(str(exc)) from exc

        try:
            data = response.json()
        except ValueError as exc:  # pragma: no cover - UI path only
            raise RuntimeError("API returned a non-JSON response") from exc
        if not isinstance(data, dict):  # pragma: no cover - defensive
            raise RuntimeError("Unexpected payload from /v1/analysis/dignities")
        return data


    # ---- Relationship ------------------------------------------------------
    def relationship_synastry(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        data = self._post_json("/relationship/synastry", payload, timeout=60)
        if not isinstance(data, dict):  # pragma: no cover - defensive
            raise RuntimeError("Unexpected response payload from /relationship/synastry")
        return data

    def relationship_composite(
        self,
        payload: Dict[str, Any],
        *,
        houses: bool = False,
        hsys: str = "P",
    ) -> Dict[str, Any]:
        params = {"houses": str(bool(houses)).lower(), "hsys": hsys}
        data = self._post_json("/relationship/composite", payload, timeout=30, params=params)
        if not isinstance(data, dict):  # pragma: no cover - defensive
            raise RuntimeError("Unexpected response payload from /relationship/composite")
        return data

    def relationship_davison(
        self,
        payload: Dict[str, Any],
        *,
        houses: bool = False,
        hsys: str = "P",
    ) -> Dict[str, Any]:
        params = {"houses": str(bool(houses)).lower(), "hsys": hsys}
        data = self._post_json("/relationship/davison", payload, timeout=60, params=params)
        if not isinstance(data, dict):  # pragma: no cover - defensive
            raise RuntimeError("Unexpected response payload from /relationship/davison")
        return data

