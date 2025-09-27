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

    def delete_policy(self, policy_id: int) -> None:
        r = requests.delete(f"{self.base}/policies/{policy_id}", timeout=30)
        if r.status_code not in (200, 204):
            r.raise_for_status()

    # ---- Arabic Lots -------------------------------------------------------
    def lots_catalog(self) -> Dict[str, Any]:
        r = requests.get(f"{self.base}/lots/catalog", timeout=30)
        r.raise_for_status(); return r.json()

    def lots_compute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        r = requests.post(f"{self.base}/lots/compute", json=payload, timeout=60)
        r.raise_for_status(); return r.json()

