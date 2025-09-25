# >>> AUTO-GEN BEGIN: userdata-vault v1.0
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from ..infrastructure.home import ae_home

BASE = ae_home() / "natals"
BASE.mkdir(parents=True, exist_ok=True)


@dataclass
class Natal:
    natal_id: str
    name: str | None
    utc: str  # ISO-8601 birth time (UTC)
    lat: float
    lon: float
    tz: str | None = None
    place: str | None = None


def _path(natal_id: str) -> Path:
    return BASE / f"{natal_id}.json"


def save_natal(n: Natal) -> Path:
    p = _path(n.natal_id)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(asdict(n), f, indent=2)
    return p


def load_natal(natal_id: str) -> Natal:
    p = _path(natal_id)
    with open(p, encoding="utf-8") as f:
        data = json.load(f)
    return Natal(**data)


def list_natals() -> list[str]:
    return sorted([p.stem for p in BASE.glob("*.json")])


def delete_natal(natal_id: str) -> bool:
    p = _path(natal_id)
    if p.exists():
        p.unlink()
        return True
    return False


# >>> AUTO-GEN END: userdata-vault v1.0
