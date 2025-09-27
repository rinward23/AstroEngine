from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple, Union

Number = Union[int, float]

# --------------------------- Angle utils -----------------------------------

def norm360(x: float) -> float:
    v = x % 360.0
    return v + 360.0 if v < 0 else v


def deg_add(a: float, b: float) -> float:
    return norm360(float(a) + float(b))


def deg_sub(a: float, b: float) -> float:
    return norm360(float(a) - float(b))


# --------------------------- Formula parser --------------------------------
# Minimal DSL: tokens separated by space. Allowed tokens:
#   - Symbol names: [A-Za-z0-9_]+ (e.g., Asc, Sun, Moon, Lot_Foo)
#   - Numbers: 0..360 (floats allowed)
#   - Operators: '+' '-'
# Grammar: Expr := Term { ('+'|'-') Term }*
# Term  := Symbol | Number

@dataclass
class Term:
    kind: str  # 'sym' or 'num'
    value: Union[str, float]


def _tokenize(expr: str) -> List[str]:
    # Allow arbitrary whitespace
    parts = expr.replace("\t", " ").strip().split()
    if not parts:
        raise ValueError("Empty formula expression")
    return parts


def _parse(expr: str) -> List[Tuple[str, Term]]:
    toks = _tokenize(expr)
    out: List[Tuple[str, Term]] = []
    op = '+'  # implicit leading '+'
    expect_term = True
    for tk in toks:
        if expect_term:
            # term
            try:
                val = float(tk)
                term = Term('num', float(val))
            except ValueError:
                # symbol
                if not tk.replace('_', '').isalnum():
                    raise ValueError(f"Invalid symbol: {tk}")
                term = Term('sym', tk)
            out.append((op, term))
            expect_term = False
        else:
            # operator
            if tk not in ('+', '-'):
                raise ValueError(f"Expected operator '+/-', got: {tk}")
            op = tk
            expect_term = True
    if expect_term:
        raise ValueError("Formula ended with operator; missing term")
    return out


def eval_formula(expr: str, pos: Dict[str, float]) -> float:
    """Evaluate an expression at positions `pos`.
    Unknown symbols raise KeyError.
    """
    seq = _parse(expr)
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
