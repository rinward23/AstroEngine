"""Built-in Arabic Lots profiles."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ...infrastructure.paths import registry_dir
from .dsl import LotProgram, compile_program, parse_lot_defs

__all__ = ["LotsProfile", "builtin_profile", "list_builtin_profiles", "load_custom_profiles", "save_custom_profile"]


@dataclass(frozen=True)
class LotsProfile:
    profile_id: str
    name: str
    description: str
    zodiac: str
    house_system: str
    policy_id: str
    expr_text: str
    source_refs: dict[str, str]
    ayanamsha: str | None = None
    tradition: str | None = None

    def program(self) -> LotProgram:
        return parse_lot_defs(self.expr_text)

    def compile(self):
        return compile_program(self.program())


_HELLENISTIC_TEXT = """
Fortune = if_day( ASC + arc(Moon, Sun), ASC + arc(Sun, Moon) )
Spirit = if_day( ASC + arc(Sun, Moon), ASC + arc(Moon, Sun) )
Eros = Fortune + arc(Venus, Spirit)
Necessity = Fortune + arc(Saturn, Spirit)
Courage = Fortune + arc(Mars, Spirit)
Marriage = Fortune + arc(Venus, Moon)
Children = Fortune + arc(Jupiter, Moon)
Travel = Fortune + arc(Mercury, Spirit)
""".strip()

_MEDIEVAL_TEXT = """
Fortune = if_day( ASC + arc(Moon, Sun), ASC + arc(Sun, Moon) )
Spirit = if_day( ASC + arc(Sun, Moon), ASC + arc(Moon, Sun) )
Eros = Fortune + arc(Venus, Spirit)
Necessity = Fortune + arc(Saturn, Spirit)
Courage = Fortune + arc(Mars, Spirit)
Marriage = Fortune + arc(Venus, Sun)
Children = Fortune + arc(Jupiter, Sun)
Travel = Fortune + arc(Mercury, Sun)
""".strip()

_BUILTINS = {
    "Hellenistic": LotsProfile(
        profile_id="lots_hellenistic",
        name="Hellenistic Core Lots",
        description="Canonical Hermetic lots per Valens and Dorotheus with day/night branches.",
        zodiac="tropical",
        house_system="Placidus",
        policy_id="standard",
        expr_text=_HELLENISTIC_TEXT,
        source_refs={
            "Fortune": "Valens, Anthologies II",
            "Spirit": "Valens, Anthologies II",
            "Eros": "Valens, Anthologies IV",
            "Necessity": "Valens, Anthologies IV",
            "Courage": "Valens, Anthologies IV",
            "Marriage": "Dorotheus, Carmen Astrologicum IV",
            "Children": "Valens, Anthologies II",
            "Travel": "Dorotheus, Carmen Astrologicum II",
        },
        tradition="Hellenistic",
    ),
    "Medieval": LotsProfile(
        profile_id="lots_medieval",
        name="Medieval Core Lots",
        description="Lots adapted for medieval authors with solar references in nocturnal charts.",
        zodiac="tropical",
        house_system="Placidus",
        policy_id="standard",
        expr_text=_MEDIEVAL_TEXT,
        source_refs={
            "Fortune": "Abu Ma'shar, The Great Introduction VI",
            "Spirit": "Abu Ma'shar, The Great Introduction VI",
            "Eros": "Bonatti, Book of Astronomy X",
            "Necessity": "Bonatti, Book of Astronomy X",
            "Courage": "Bonatti, Book of Astronomy X",
            "Marriage": "Abu Ma'shar, Great Introduction VIII",
            "Children": "Abu Ma'shar, Great Introduction VIII",
            "Travel": "Bonatti, Book of Astronomy IX",
        },
        tradition="Medieval",
    ),
}


def list_builtin_profiles() -> list[LotsProfile]:
    return list(_BUILTINS.values())


def builtin_profile(tradition: Literal["Hellenistic", "Medieval"] = "Hellenistic") -> LotsProfile:
    try:
        return _BUILTINS[tradition]
    except KeyError as exc:
        raise ValueError(f"Unknown lots tradition: {tradition}") from exc


_CUSTOM_PATH = registry_dir() / "lots_custom_profiles.json"


def load_custom_profiles() -> dict[str, LotsProfile]:
    if not _CUSTOM_PATH.exists():
        return {}
    data = _CUSTOM_PATH.read_text(encoding="utf-8")
    import json

    payload = json.loads(data)
    profiles: dict[str, LotsProfile] = {}
    for item in payload:
        profile = LotsProfile(
            profile_id=item["profile_id"],
            name=item["name"],
            description=item.get("description", ""),
            zodiac=item.get("zodiac", "tropical"),
            house_system=item.get("house_system", "Placidus"),
            policy_id=item.get("policy_id", "standard"),
            expr_text=item["expr_text"],
            source_refs=item.get("source_refs", {}),
            ayanamsha=item.get("ayanamsha"),
            tradition=item.get("tradition"),
        )
        profiles[profile.profile_id] = profile
    return profiles


def save_custom_profile(profile: LotsProfile) -> None:
    import json

    profiles = load_custom_profiles()
    profiles[profile.profile_id] = profile
    payload = [
        {
            "profile_id": item.profile_id,
            "name": item.name,
            "description": item.description,
            "zodiac": item.zodiac,
            "house_system": item.house_system,
            "policy_id": item.policy_id,
            "expr_text": item.expr_text,
            "source_refs": item.source_refs,
            "ayanamsha": item.ayanamsha,
            "tradition": item.tradition,
        }
        for item in profiles.values()
    ]
    _CUSTOM_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CUSTOM_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
