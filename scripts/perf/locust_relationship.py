"""Locust user flows targeting relationship endpoints with cache-aware ratios."""
from __future__ import annotations

from random import randint

from locust import HttpUser, between, task


class RelationshipUser(HttpUser):
    wait_time = between(0.2, 1.2)

    _syn_payload = {
        "pos_a": {f"A{i}": (i * 17) % 360 for i in range(1, 14)},
        "pos_b": {f"B{i}": (i * 23 + 45) % 360 for i in range(1, 14)},
        "aspects": [
            "conjunction",
            "opposition",
            "square",
            "trine",
            "sextile",
            "quincunx",
            "semisquare",
            "sesquisquare",
            "quintile",
            "biquintile",
        ],
    }

    @task(7)
    def warm_synastry(self) -> None:
        self.client.post("/synastry/compute", json=self._syn_payload)

    @task(2)
    def variant_synastry(self) -> None:
        payload = dict(self._syn_payload)
        payload["pos_a"] = {k: (v + randint(0, 15)) % 360 for k, v in payload["pos_a"].items()}
        self.client.post("/synastry/compute", json=payload)

    @task(1)
    def davison(self) -> None:
        self.client.post(
            "/composites/davison",
            json={
                "objects": ["Sun", "Venus", "Mars"],
                "dt_a": "2025-01-01T00:00:00Z",
                "dt_b": "2025-01-10T00:00:00Z",
                "lat_a": 40.7,
                "lon_a": -74.0,
                "lat_b": 34.0,
                "lon_b": -118.2,
            },
        )
