# >>> AUTO-GEN BEGIN: userdata-vault v1.0
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from ..infrastructure.home import ae_home
from ..chart.config import ChartConfig

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
    house_system: str = "placidus"
    zodiac: str = "tropical"
    ayanamsa: str | None = None

    def chart_config(self) -> ChartConfig:
        """Return a normalized :class:`ChartConfig` for this natal record."""

        return ChartConfig(
            zodiac=self.zodiac,
            ayanamsha=self.ayanamsa,
            house_system=self.house_system,
        )


def _path(natal_id: str) -> Path:
    return BASE / f"{natal_id}.json"


def save_natal(n: Natal) -> Path:
    p = _path(n.natal_id)
    with open(p, "w", encoding="utf-8") as f:
        data = asdict(n)
        data["houses"] = {"system": n.house_system}
        zodiac_payload: dict[str, object] = {"type": n.zodiac}
        if n.ayanamsa is not None:
            zodiac_payload["ayanamsa"] = n.ayanamsa
        data["zodiac"] = zodiac_payload
        json.dump(data, f, indent=2)
    return p


def load_natal(natal_id: str) -> Natal:
    p = _path(natal_id)
    with open(p, encoding="utf-8") as f:
        data = json.load(f)
    houses_payload = data.pop("houses", None)
    if isinstance(houses_payload, dict):
        system = houses_payload.get("system")
        if system is not None:
            data.setdefault("house_system", system)
    zodiac_payload = data.pop("zodiac", None)
    if isinstance(zodiac_payload, dict):
        zodiac_type = zodiac_payload.get("type")
        if zodiac_type is not None:
            data.setdefault("zodiac", zodiac_type)
        if "ayanamsa" in zodiac_payload:
            ayanamsa_value = zodiac_payload.get("ayanamsa")
            data.setdefault("ayanamsa", ayanamsa_value)
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
