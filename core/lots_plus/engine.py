from __future__ import annotations
from typing import Dict

from core.lots_plus.parser import Number, Term, parse_formula

# --------------------------- Angle utils -----------------------------------

def norm360(x: float) -> float:
    v = x % 360.0
    return v + 360.0 if v < 0 else v


def deg_add(a: float, b: float) -> float:
    return norm360(float(a) + float(b))


def deg_sub(a: float, b: float) -> float:
    return norm360(float(a) - float(b))


def eval_formula(expr: str, pos: Dict[str, float]) -> float:
    """Evaluate an expression at positions `pos`.
    Unknown symbols raise KeyError.
    """
    seq = parse_formula(expr)
    acc = 0.0
    for op, term in seq:
        if term.kind == 'num':
            val = float(term.value)
        else:
            name = str(term.value)
            if name not in pos:
                raise KeyError(f"Missing symbol in positions: {name}")
            val = float(pos[name])
        acc = deg_add(acc, val) if op == '+' else deg_sub(acc, val)
    return norm360(acc)


__all__ = [
    "Number",
    "norm360",
    "deg_add",
    "deg_sub",
    "Term",
    "eval_formula",
]
