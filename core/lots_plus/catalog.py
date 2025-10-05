from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Set

from core.lots_plus.engine import eval_formula
from core.lots_plus.parser import extract_symbols


@dataclass
class LotDef:
    name: str
    day: str  # expression for day sect
    night: str  # expression for night sect
    description: str = ""


# Built-in catalog (ecliptic longitudes)
# Conventional formulas (Hellenistic/medieval):
#  Fortune  (Tyche):   day = Asc + Moon - Sun ; night = Asc + Sun - Moon
#  Spirit   (Daimon):  day = Asc + Sun - Moon ; night = Asc + Moon - Sun
#  Eros                day = Asc + Venus - Spirit ; night = Asc + Spirit - Venus
#  Necessity           day = Asc + Spirit - Mercury ; night = Asc + Mercury - Spirit
#  Victory (Nike)      day = Asc + Jupiter - Spirit ; night = Asc + Spirit - Jupiter
BUILTIN: Dict[str, LotDef] = {
    "Fortune": LotDef("Fortune", day="Asc + Moon - Sun", night="Asc + Sun - Moon", description="Part of Fortune (Tyche)"),
    "Spirit": LotDef("Spirit", day="Asc + Sun - Moon", night="Asc + Moon - Sun", description="Part of Spirit (Daimon)"),
    "Eros": LotDef("Eros", day="Asc + Venus - Spirit", night="Asc + Spirit - Venus", description="Part of Eros"),
    "Necessity": LotDef("Necessity", day="Asc + Spirit - Mercury", night="Asc + Mercury - Spirit", description="Part of Necessity"),
    "Victory": LotDef("Victory", day="Asc + Jupiter - Spirit", night="Asc + Spirit - Jupiter", description="Part of Victory (Nike)"),
}

# Runtime registry (starts with BUILTIN; can be extended)
REGISTRY: Dict[str, LotDef] = dict(BUILTIN)


def register_lot(defn: LotDef, overwrite: bool = False) -> None:
    key = defn.name
    if not overwrite and key in REGISTRY:
        raise KeyError(f"Lot already exists: {key}")
    REGISTRY[key] = defn


def unregister_lot(name: str) -> None:
    REGISTRY.pop(name, None)


class Sect:
    DAY = "day"
    NIGHT = "night"


def compute_lot(name: str, pos: Dict[str, float], sect: str, _stack: Optional[Set[str]] = None) -> float:
    if sect not in (Sect.DAY, Sect.NIGHT):
        raise ValueError(f"Invalid sect: {sect}")
    if name not in REGISTRY:
        raise KeyError(f"Unknown lot: {name}")

    stack = set() if _stack is None else set(_stack)
    if name in stack:
        raise ValueError(f"Circular lot dependency detected: {' -> '.join(list(stack) + [name])}")
    stack.add(name)

    lot = REGISTRY[name]
    expr = lot.day if sect == Sect.DAY else lot.night

    # Prepare a working copy of positions so we can inject dependent lot values.
    working_pos = dict(pos)
    for symbol in extract_symbols(expr):
        if symbol in working_pos or symbol == name:
            continue
        if symbol in REGISTRY:
            working_pos[symbol] = compute_lot(symbol, pos, sect, stack)

    return eval_formula(expr, working_pos)


def compute_lots(names: Iterable[str], pos: Dict[str, float], sect: str) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for n in names:
        out[n] = compute_lot(n, pos, sect)
    return out


__all__ = [
    "LotDef",
    "BUILTIN",
    "REGISTRY",
    "register_lot",
    "unregister_lot",
    "Sect",
    "compute_lot",
    "compute_lots",
]
