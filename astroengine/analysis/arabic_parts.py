"""Arabic Parts (Lots) computation utilities."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import math
import re
from typing import Iterable, Iterator, Mapping, MutableMapping

from astroengine.chart.natal import NatalChart
from astroengine.engine.lots.sect import GeoLocation, is_day as chart_is_day
from astroengine.jyotish.utils import house_index_for

__all__ = [
    "ArabicPartError",
    "LotDefinition",
    "ComputedLot",
    "ArabicPartsComputation",
    "PRESET_DEFINITIONS",
    "compute_lot",
    "compute_all",
]


class ArabicPartError(RuntimeError):
    """Raised when a lot definition cannot be evaluated."""


@dataclass(frozen=True)
class LotDefinition:
    """Simple structure describing an Arabic Part formula."""

    name: str
    day: str
    night: str | None = None
    description: str | None = None

    def formula(self, is_day: bool) -> str:
        if is_day or not self.night:
            return self.day
        return self.night


@dataclass(frozen=True)
class ComputedLot:
    """Result payload for a computed Arabic Part."""

    name: str
    longitude: float
    house: int | None
    description: str | None
    source: str
    day_formula: str
    night_formula: str


@dataclass(frozen=True)
class ArabicPartsComputation:
    """Collection of computed lots and contextual metadata."""

    is_day: bool
    lots: tuple[ComputedLot, ...]
    metadata: Mapping[str, object]


_PRESET_LIST: tuple[LotDefinition, ...] = (
    LotDefinition(
        name="Fortune",
        day="ASC + Moon - Sun",
        night="ASC + Sun - Moon",
        description="Part of Fortune (Tyche)",
    ),
    LotDefinition(
        name="Spirit",
        day="ASC + Sun - Moon",
        night="ASC + Moon - Sun",
        description="Part of Spirit (Daimon)",
    ),
    LotDefinition(
        name="Eros",
        day="ASC + Venus - Lot(Spirit)",
        night="ASC + Lot(Spirit) - Venus",
        description="Part of Eros",
    ),
)

PRESET_DEFINITIONS: Mapping[str, LotDefinition] = {
    definition.name: definition for definition in _PRESET_LIST
}

_TOKEN_PATTERN = re.compile(
    r"\s*"  # Leading whitespace
    r"("  # Capture group for the token
    r"Lot\(\s*[^()]+?\s*\)"  # Lot(Name)
    r"|[A-Za-z_][A-Za-z0-9_]*"  # Symbols (Sun, Moon, ASC, Venus, etc.)
    r"|[+-]"  # Operators
    r"|\d+(?:\.\d+)?"  # Numbers
    r")",
)


@dataclass(frozen=True)
class _Term:
    op: str
    kind: str
    value: object


def _norm360(value: float) -> float:
    v = math.fmod(value, 360.0)
    if v < 0:
        v += 360.0
    return v


def _deg_add(a: float, b: float) -> float:
    return _norm360(float(a) + float(b))


def _deg_sub(a: float, b: float) -> float:
    return _norm360(float(a) - float(b))


def _tokenize(expr: str) -> Iterator[str]:
    pos = 0
    length = len(expr)
    while pos < length:
        match = _TOKEN_PATTERN.match(expr, pos)
        if not match:
            raise ArabicPartError(f"Unexpected token near '{expr[pos:pos+10]}...'")
        token = match.group(1)
        pos = match.end()
        if token.strip():
            yield token.strip()


@lru_cache(maxsize=256)
def _parse(expr: str) -> tuple[_Term, ...]:
    if not expr or not expr.strip():
        raise ArabicPartError("Formula must not be empty")
    tokens = list(_tokenize(expr))
    if not tokens:
        raise ArabicPartError("Formula must not be empty")

    terms: list[_Term] = []
    op = "+"
    expect_term = True
    for token in tokens:
        if expect_term:
            if token in {"+", "-"}:
                raise ArabicPartError("Formula cannot have consecutive operators")
            if token.lower().startswith("lot(") and token.endswith(")"):
                inner = token[4:-1].strip()
                if not inner:
                    raise ArabicPartError("Lot() requires a name")
                terms.append(_Term(op=op, kind="lot", value=inner))
            else:
                try:
                    value = float(token)
                except ValueError:
                    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", token):
                        raise ArabicPartError(f"Invalid symbol '{token}' in formula")
                    terms.append(_Term(op=op, kind="symbol", value=token))
                else:
                    terms.append(_Term(op=op, kind="number", value=value))
            expect_term = False
        else:
            if token not in {"+", "-"}:
                raise ArabicPartError("Expected '+' or '-' between terms")
            op = token
            expect_term = True
    if expect_term:
        raise ArabicPartError("Formula cannot end with an operator")
    return tuple(terms)


def _base_positions(chart: NatalChart) -> Mapping[str, float]:
    positions = {name.upper(): pos.longitude for name, pos in chart.positions.items()}
    positions["ASC"] = chart.houses.ascendant
    return positions


def _resolve_symbol(
    term: _Term,
    chart: NatalChart,
    definitions: Mapping[str, LotDefinition],
    memo: MutableMapping[str, float],
    is_diurnal: bool,
    stack: set[str],
    base_positions: Mapping[str, float],
) -> float:
    if term.kind == "number":
        return float(term.value)
    if term.kind == "symbol":
        key = str(term.value).upper()
        if key in base_positions:
            return float(base_positions[key])
        raise ArabicPartError(f"Symbol '{term.value}' is not available in chart positions")
    if term.kind == "lot":
        return _compute_named_lot(
            str(term.value),
            chart,
            definitions,
            memo,
            is_diurnal,
            stack,
            base_positions,
        )
    raise ArabicPartError(f"Unsupported term type '{term.kind}'")


def _compute_named_lot(
    name: str,
    chart: NatalChart,
    definitions: Mapping[str, LotDefinition],
    memo: MutableMapping[str, float],
    is_diurnal: bool,
    stack: set[str],
    base_positions: Mapping[str, float],
) -> float:
    key = name.casefold()
    if key in memo:
        return memo[key]
    if key in stack:
        path = " -> ".join(list(stack) + [name])
        raise ArabicPartError(f"Circular lot dependency detected: {path}")

    definition = definitions.get(key)
    if not definition:
        raise ArabicPartError(f"Lot '{name}' is not defined")

    stack.add(key)
    expr = definition.formula(is_diurnal)
    terms = _parse(expr)
    acc = 0.0
    for term in terms:
        value = _resolve_symbol(term, chart, definitions, memo, is_diurnal, stack, base_positions)
        acc = _deg_add(acc, value) if term.op == "+" else _deg_sub(acc, value)
    stack.remove(key)
    result = _norm360(acc)
    memo[key] = result
    return result


def _definitions_with_presets(
    presets: Iterable[LotDefinition],
    custom: Iterable[LotDefinition],
) -> tuple[Mapping[str, LotDefinition], list[str], list[str]]:
    mapping: dict[str, LotDefinition] = {}
    preset_names: list[str] = []
    custom_names: list[str] = []
    for definition in presets:
        key = definition.name.casefold()
        mapping[key] = definition
        preset_names.append(definition.name)
    for definition in custom:
        key = definition.name.casefold()
        mapping[key] = definition
        custom_names.append(definition.name)
    # Ensure all presets are available for dependency resolution.
    for definition in _PRESET_LIST:
        mapping.setdefault(definition.name.casefold(), definition)
    return mapping, preset_names, custom_names


def compute_lot(name: str, chart: NatalChart, is_diurnal: bool) -> float:
    """Compute a preset Arabic Part by ``name`` for ``chart``."""

    definitions, _, _ = _definitions_with_presets(_PRESET_LIST, ())
    base_positions = _base_positions(chart)
    return _compute_named_lot(name, chart, definitions, {}, is_diurnal, set(), base_positions)


def compute_all(settings, chart: NatalChart) -> ArabicPartsComputation:
    """Compute all enabled Arabic Parts for ``chart`` respecting ``settings``."""

    arabic_cfg = getattr(settings, "arabic_parts", None)
    if arabic_cfg is None:
        raise ArabicPartError("Settings missing 'arabic_parts' configuration")

    geolocation = GeoLocation(
        latitude=float(chart.location.latitude),
        longitude=float(chart.location.longitude),
    )
    is_diurnal = chart_is_day(chart.moment, geolocation)

    enabled_presets: list[LotDefinition] = []
    preset_flags = getattr(arabic_cfg, "presets", {})
    for definition in _PRESET_LIST:
        if preset_flags.get(definition.name, False):
            enabled_presets.append(definition)

    custom_defs: list[LotDefinition] = []
    for custom in getattr(arabic_cfg, "custom", []):
        night_formula = custom.night if getattr(custom, "night", None) else custom.day
        custom_defs.append(
            LotDefinition(
                name=custom.name,
                day=custom.day,
                night=night_formula,
                description=getattr(custom, "description", None),
            )
        )

    definitions, preset_order, custom_order = _definitions_with_presets(
        enabled_presets, custom_defs
    )
    base_positions = _base_positions(chart)
    memo: dict[str, float] = {}
    results: list[ComputedLot] = []

    def _result_for(name: str, source: str) -> ComputedLot:
        value = _compute_named_lot(
            name,
            chart,
            definitions,
            memo,
            is_diurnal,
            set(),
            base_positions,
        )
        definition = definitions[name.casefold()]
        house = None
        if chart.houses.cusps:
            try:
                house = int(house_index_for(value, chart.houses))
            except Exception:  # pragma: no cover - defensive
                house = None
        return ComputedLot(
            name=definition.name,
            longitude=value,
            house=house,
            description=definition.description,
            source=source,
            day_formula=definition.day,
            night_formula=definition.night or definition.day,
        )

    for name in preset_order:
        results.append(_result_for(name, "preset"))
    for name in custom_order:
        results.append(_result_for(name, "custom"))

    metadata: dict[str, object] = {
        "house_system": chart.houses.system,
        "zodiac": chart.zodiac,
    }
    if chart.ayanamsa:
        metadata["ayanamsa"] = chart.ayanamsa
    if chart.ayanamsa_degrees is not None:
        metadata["ayanamsa_degrees"] = chart.ayanamsa_degrees

    return ArabicPartsComputation(
        is_day=is_diurnal,
        lots=tuple(results),
        metadata=metadata,
    )
