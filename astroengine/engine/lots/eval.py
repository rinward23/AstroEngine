"""Evaluation of compiled Arabic Lots programs."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Mapping, MutableMapping

from ...chart.natal import ChartLocation
from .dsl import (
    Add,
    Arc,
    CompiledProgram,
    Expr,
    IfDay,
    LotProgram,
    Number,
    Ref,
    Sub,
    Wrap,
    compile_program,
    parse_lot_defs,
)
from .sect import GeoLocation, is_day as _is_day

__all__ = [
    "ChartContext",
    "ChartLocation",
    "evaluate",
    "prepare_program",
]


@dataclass(frozen=True)
class ChartContext:
    """Context required to evaluate Arabic Lots."""

    moment: datetime | None
    location: ChartLocation | None
    positions: Mapping[str, float]
    angles: Mapping[str, float] = field(default_factory=dict)
    is_day_override: bool | None = None
    sun_altitude: float | None = None
    zodiac: str = "tropical"
    ayanamsha: str | None = None
    house_system: str | None = None

    def get_point(self, name: str) -> float:
        key = name.strip()
        if key in self.positions:
            return float(self.positions[key]) % 360.0
        if key in self.angles:
            return float(self.angles[key]) % 360.0
        raise KeyError(f"Unknown point: {name}")

    def is_day(self) -> bool:
        if self.is_day_override is not None:
            return bool(self.is_day_override)
        if self.moment is None or self.location is None:
            raise ValueError("moment and location are required for sect determination")
        geo = GeoLocation(self.location.latitude, self.location.longitude)
        return _is_day(self.moment, geo, sun_altitude=self.sun_altitude)


def prepare_program(text: str | LotProgram | CompiledProgram) -> CompiledProgram:
    if isinstance(text, CompiledProgram):
        return text
    if isinstance(text, LotProgram):
        return compile_program(text)
    program = parse_lot_defs(text)
    return compile_program(program)


def _wrap(value: float) -> float:
    return value % 360.0


def _arc(first: float, second: float) -> float:
    return (first - second) % 360.0


def _evaluate_expr(
    expr: Expr,
    ctx: ChartContext,
    results: MutableMapping[str, float],
) -> float:
    if isinstance(expr, Number):
        return _wrap(expr.value)
    if isinstance(expr, Ref):
        name = expr.name
        if name in results:
            return results[name]
        return ctx.get_point(name)
    if isinstance(expr, Add):
        return _wrap(_evaluate_expr(expr.left, ctx, results) + _evaluate_expr(expr.right, ctx, results))
    if isinstance(expr, Sub):
        return _wrap(_evaluate_expr(expr.left, ctx, results) - _evaluate_expr(expr.right, ctx, results))
    if isinstance(expr, Arc):
        return _arc(
            _evaluate_expr(expr.first, ctx, results),
            _evaluate_expr(expr.second, ctx, results),
        )
    if isinstance(expr, Wrap):
        return _wrap(_evaluate_expr(expr.value, ctx, results))
    if isinstance(expr, IfDay):
        branch = expr.day_expr if ctx.is_day() else expr.night_expr
        return _wrap(_evaluate_expr(branch, ctx, results))
    raise TypeError(f"Unsupported expression {expr!r}")


def evaluate(program: CompiledProgram, chart: ChartContext) -> dict[str, float]:
    """Evaluate ``program`` returning normalized lot positions."""

    results: dict[str, float] = {}
    for name in program.order:
        expr = program.definitions[name]
        value = _evaluate_expr(expr, chart, results)
        results[name] = _wrap(value)
    return results
